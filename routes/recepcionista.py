from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import Sala, Reserva, BloqueioSala, Usuario
from extensions import db
from services.disponibilidade import (
    horario_disponivel,
    criar_bloqueios_automaticos,
    remover_bloqueios_automaticos,
)
from services.recorrencia import criar_bloqueio_recorrente
from services.auditoria import registrar_log
from services.notificacoes import notificar_reserva_cancelada, notificar_reserva_movida

recepcionista_bp = Blueprint("recepcionista", __name__, url_prefix="/recepcionista")


def apenas_recepcionista(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if current_user.nivel not in ("recepcionista", "administrador"):
            flash("Acesso não autorizado.", "erro")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorador


@recepcionista_bp.route("/painel")
@login_required
@apenas_recepcionista
def painel():
    salas = Sala.query.filter_by(ativa=True).all()

    # Filtro por período (padrão: hoje). Aceita ?data=AAAA-MM-DD (dia único)
    # ou ?data_ini=AAAA-MM-DD&data_fim=AAAA-MM-DD (período).
    hoje = datetime.now().date()
    data_str = request.args.get("data")
    data_ini_str = request.args.get("data_ini")
    data_fim_str = request.args.get("data_fim")

    def _parse_data(valor):
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    if data_ini_str or data_fim_str:
        data_ini = _parse_data(data_ini_str) or hoje
        data_fim = _parse_data(data_fim_str) or data_ini
        if data_fim < data_ini:
            data_ini, data_fim = data_fim, data_ini
        modo_periodo = True
    else:
        data_ini = _parse_data(data_str) or hoje
        data_fim = data_ini
        modo_periodo = False

    inicio_dia = datetime.combine(data_ini, datetime.min.time())
    fim_dia = datetime.combine(data_fim, datetime.max.time())

    reservas = Reserva.query.filter(
        Reserva.status != "cancelada",
        Reserva.inicio >= inicio_dia,
        Reserva.inicio <= fim_dia,
    ).order_by(Reserva.inicio).all()

    return render_template(
        "recepcionista_painel.html",
        salas=salas,
        reservas=reservas,
        data_filtro=data_ini,
        data_ini=data_ini,
        data_fim=data_fim,
        modo_periodo=modo_periodo,
        hoje=hoje,
    )


@recepcionista_bp.route("/calendario")
@login_required
@apenas_recepcionista
def calendario():
    return render_template("recepcionista_calendario.html")


@recepcionista_bp.route("/reserva/nova", methods=["GET", "POST"])
@login_required
@apenas_recepcionista
def nova_reserva_para_colaborador():
    salas = Sala.query.filter_by(ativa=True).all()
    usuarios = Usuario.query.filter_by(ativo=True).all()

    if request.method == "POST":
        sala_id = int(request.form["sala_id"])
        usuario_id = int(request.form["usuario_id"])
        titulo = request.form["titulo"].strip()
        inicio = datetime.strptime(request.form["inicio"], "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(request.form["fim"], "%Y-%m-%dT%H:%M")

        disponivel, mensagem = horario_disponivel(sala_id, inicio, fim)
        if not disponivel:
            flash(mensagem, "erro")
            return render_template("nova_reserva.html", salas=salas, usuarios=usuarios)

        reserva = Reserva(
            sala_id=sala_id,
            usuario_id=usuario_id,
            criado_por_id=current_user.id,
            titulo=titulo,
            inicio=inicio,
            fim=fim,
        )
        db.session.add(reserva)
        db.session.commit()
        criar_bloqueios_automaticos(reserva)

        flash("Reunião marcada com sucesso!", "sucesso")
        return redirect(url_for("recepcionista.painel"))

    return render_template("nova_reserva.html", salas=salas, usuarios=usuarios)

@recepcionista_bp.route("/reserva/<int:reserva_id>/excluir", methods=["POST"])
@login_required
@apenas_recepcionista
def excluir_reserva(reserva_id):
    from models import Reserva
    reserva = db.get_or_404(Reserva, reserva_id)
    reserva.status = "cancelada"
    remover_bloqueios_automaticos(reserva.id)
    db.session.commit()

    registrar_log("cancelou_reserva", "reserva", reserva.id, f"Sala: {reserva.sala.nome}")
    notificar_reserva_cancelada(reserva)

    flash("Reunião excluída.", "sucesso")
    return redirect(url_for("recepcionista.painel"))


@recepcionista_bp.route("/reserva/<int:reserva_id>/mover", methods=["POST"])
@login_required
@apenas_recepcionista
def mover_reserva(reserva_id):
    from models import Reserva
    reserva = db.get_or_404(Reserva, reserva_id)
    nova_sala_id = int(request.form["nova_sala_id"])
    sala_antiga_nome = reserva.sala.nome

    disponivel, mensagem = horario_disponivel(
        nova_sala_id, reserva.inicio, reserva.fim, ignorar_reserva_id=reserva.id
    )
    if not disponivel:
        flash(mensagem, "erro")
        return redirect(url_for("recepcionista.painel"))

    remover_bloqueios_automaticos(reserva.id)
    reserva.sala_id = nova_sala_id
    db.session.commit()
    criar_bloqueios_automaticos(reserva)

    registrar_log("moveu_reserva", "reserva", reserva.id, f"De {sala_antiga_nome} para {reserva.sala.nome}")
    notificar_reserva_movida(reserva, sala_antiga_nome)

    flash("Reunião movida com sucesso.", "sucesso")
    return redirect(url_for("recepcionista.painel"))

@recepcionista_bp.route("/sala/bloquear", methods=["GET", "POST"])
@login_required
@apenas_recepcionista
def bloquear_sala():
    salas = Sala.query.filter_by(ativa=True).all()

    if request.method == "POST":
        sala_id = int(request.form["sala_id"])
        inicio = datetime.strptime(request.form["inicio"], "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(request.form["fim"], "%Y-%m-%dT%H:%M")
        motivo = request.form.get("motivo", "").strip()

        bloqueio = BloqueioSala(
            sala_id=sala_id,
            inicio=inicio,
            fim=fim,
            motivo=motivo or "Bloqueio manual",
            automatico=False,
            criado_por_id=current_user.id,
        )
        db.session.add(bloqueio)
        db.session.commit()

        flash("Sala bloqueada no período informado.", "sucesso")
        return redirect(url_for("recepcionista.painel"))

    return render_template("bloquear_sala.html", salas=salas)

@recepcionista_bp.route("/sala/bloquear-recorrente", methods=["GET", "POST"])
@login_required
@apenas_recepcionista
def bloquear_sala_recorrente():
    from models import Sala
    salas = Sala.query.filter_by(ativa=True).all()

    if request.method == "POST":
        sala_id = int(request.form["sala_id"])
        hora_inicio = datetime.strptime(request.form["hora_inicio"], "%Y-%m-%dT%H:%M")
        hora_fim = datetime.strptime(request.form["hora_fim"], "%Y-%m-%dT%H:%M")
        data_ate = datetime.strptime(request.form["data_ate"], "%Y-%m-%d")
        dias_semana = [int(d) for d in request.form.getlist("dias_semana")]
        motivo = request.form.get("motivo", "Bloqueio recorrente")

        if not dias_semana:
            flash("Selecione ao menos um dia da semana.", "erro")
            return render_template("bloquear_sala_recorrente.html", salas=salas)

        bloqueios, grupo_id = criar_bloqueio_recorrente(
            sala_id, hora_inicio, hora_fim, dias_semana, data_ate, motivo, current_user.id
        )

        registrar_log(
            "bloqueio_recorrente_criado", "bloqueio", None,
            f"Grupo {grupo_id}: {len(bloqueios)} bloqueios criados na sala {sala_id}"
        )

        flash(f"{len(bloqueios)} bloqueios recorrentes criados com sucesso.", "sucesso")
        return redirect(url_for("recepcionista.painel"))

    return render_template("bloquear_sala_recorrente.html", salas=salas)
