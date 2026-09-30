import re
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import Sala, Reserva
from extensions import db
from services.disponibilidade import horario_disponivel, criar_bloqueios_automaticos
from services.auditoria import registrar_log
from services.notificacoes import notificar_reserva_criada
from services.auditoria import registrar_log
from services.notificacoes import notificar_reserva_cancelada
from models import Reserva
from flask import abort
from services.disponibilidade import (
    horario_disponivel,
    criar_bloqueios_automaticos,
    remover_bloqueios_automaticos,
)
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from models import ParticipanteReserva

colaborador_bp = Blueprint("colaborador", __name__, url_prefix="/colaborador")


DIAS_SEMANA_NOMES = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}


@colaborador_bp.route("/painel")
@login_required
def painel():
    salas = Sala.query.filter_by(ativa=True).all()
    minhas_reservas = Reserva.query.filter_by(
        usuario_id=current_user.id, status="confirmada"
    ).order_by(Reserva.inicio).all()

    # Agrupa minhas reservas recorrentes futuras (para a seção "Minhas recorrências")
    grupos = {}
    agora = datetime.now()
    for r in minhas_reservas:
        if r.grupo_recorrencia_id and r.fim >= agora:
            g = grupos.setdefault(r.grupo_recorrencia_id, {
                "grupo_id": r.grupo_recorrencia_id,
                "titulo": r.titulo,
                "sala": r.sala.nome,
                "hora": r.inicio.strftime("%H:%M"),
                "dias": sorted({DIAS_SEMANA_NOMES[d] for d in
                                [r.inicio.weekday()] + [x.inicio.weekday() for x in minhas_reservas
                                                        if x.grupo_recorrencia_id == r.grupo_recorrencia_id]}),
                "primeira": r.inicio,
                "ultima": r.inicio,
                "proximas": 0,
            })
            g["primeira"] = min(g["primeira"], r.inicio)
            g["ultima"] = max(g["ultima"], r.inicio)
            g["proximas"] += 1

    recorrencias = []
    for g in grupos.values():
        g["dias"] = ", ".join(g["dias"])
        g["periodo"] = f"{g['primeira'].strftime('%d/%m/%Y')} a {g['ultima'].strftime('%d/%m/%Y')}"
        recorrencias.append(g)
    recorrencias.sort(key=lambda g: g["primeira"])

    return render_template(
        "dashboard.html",
        salas=salas,
        reservas=minhas_reservas,
        recorrencias=recorrencias,
    )


@colaborador_bp.route("/nova-reserva", methods=["GET", "POST"])
@login_required
def nova_reserva():
    salas = Sala.query.filter_by(ativa=True).all()

    if request.method == "POST":
        sala_id = int(request.form["sala_id"])
        titulo = request.form["titulo"].strip()
        inicio = datetime.strptime(request.form["inicio"], "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(request.form["fim"], "%Y-%m-%dT%H:%M")

        if fim <= inicio:
            flash("O horário final deve ser depois do inicial.", "erro")
            return render_template("nova_reserva.html", salas=salas)

        disponivel, mensagem = horario_disponivel(sala_id, inicio, fim)
        if not disponivel:
            flash(mensagem, "erro")
            return render_template("nova_reserva.html", salas=salas)

        participantes_raw = request.form.get("participantes", "")

        # O separador oficial é vírgula. Espaço, ponto e vírgula etc. geram alerta.
        emails_participantes = [
            e.strip() for e in participantes_raw.split(",") if e.strip()
        ]

        # Valida formato de cada e-mail ANTES de criar a reserva (rejeita
        # texto com espaço, ponto e vírgula, sem @ etc. — evita erro 500 no envio).
        padrao_email = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
        emails_invalidos = [
            e for e in emails_participantes if not padrao_email.match(e)
        ]
        if emails_invalidos:
            flash(
                "E-mail(s) inválido(s): " + ", ".join(emails_invalidos)
                + ". Separe os e-mails por VÍRGULA (ex.: a@conebel.com.br, b@conebel.com.br).",
                "erro",
            )
            return render_template("nova_reserva.html", salas=salas)

        reserva = Reserva(
            sala_id=sala_id,
            usuario_id=current_user.id,
            criado_por_id=current_user.id,
            titulo=titulo,
            inicio=inicio,
            fim=fim,
        )
        db.session.add(reserva)
        db.session.commit()

        for email in emails_participantes:
            participante = ParticipanteReserva(
                reserva_id=reserva.id,
                email=email
            )
            db.session.add(participante)

        db.session.commit()

        criar_bloqueios_automaticos(reserva)

        registrar_log("criou_reserva", "reserva", reserva.id, f"Sala: {reserva.sala.nome}")
        notificar_reserva_criada(reserva)

        flash("Reserva criada com sucesso!", "sucesso")
        return redirect(url_for("colaborador.painel"))

    return render_template("nova_reserva.html", salas=salas)

@colaborador_bp.route("/reserva-recorrente", methods=["GET", "POST"])
@login_required
def reserva_recorrente():
    salas = Sala.query.filter_by(ativa=True).all()

    if request.method == "POST":
        sala_id = int(request.form["sala_id"])
        titulo = request.form["titulo"].strip()
        inicio = datetime.strptime(request.form["hora_inicio"], "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(request.form["hora_fim"], "%Y-%m-%dT%H:%M")
        data_ate = datetime.strptime(request.form["data_ate"], "%Y-%m-%d")
        dias_semana = [int(d) for d in request.form.getlist("dias_semana")]

        if not dias_semana:
            flash("Selecione ao menos um dia da semana.", "erro")
            return render_template("reserva_recorrente.html", salas=salas)
        if fim.time() <= inicio.time():
            flash("O horário final deve ser depois do inicial.", "erro")
            return render_template("reserva_recorrente.html", salas=salas)
        if data_ate.date() < inicio.date():
            flash("A data final deve ser depois do primeiro dia.", "erro")
            return render_template("reserva_recorrente.html", salas=salas)

        # Valida conflito em TODAS as ocorrências antes de criar qualquer coisa
        conflitos = []
        data_atual = inicio.date()
        while data_atual <= data_ate.date():
            if data_atual.weekday() in dias_semana:
                ini_dia = datetime.combine(data_atual, inicio.time())
                fim_dia = datetime.combine(data_atual, fim.time())
                disponivel, mensagem = horario_disponivel(sala_id, ini_dia, fim_dia)
                if not disponivel:
                    conflitos.append(f"{ini_dia.strftime('%d/%m/%Y %H:%M')} — {mensagem}")
            data_atual += timedelta(days=1)

        if conflitos:
            flash(
                "Não foi possível criar: há conflito de horário em "
                f"{len(conflitos)} ocorrência(s). Nenhuma reserva foi criada. "
                "Primeiros conflitos: " + " | ".join(conflitos[:3]),
                "erro",
            )
            return render_template("reserva_recorrente.html", salas=salas)

        # Cria todas as reservas com o mesmo grupo_recorrencia_id
        grupo_id = str(uuid.uuid4())
        criadas = 0
        data_atual = inicio.date()
        while data_atual <= data_ate.date():
            if data_atual.weekday() in dias_semana:
                ini_dia = datetime.combine(data_atual, inicio.time())
                fim_dia = datetime.combine(data_atual, fim.time())
                reserva = Reserva(
                    sala_id=sala_id,
                    usuario_id=current_user.id,
                    criado_por_id=current_user.id,
                    titulo=titulo,
                    inicio=ini_dia,
                    fim=fim_dia,
                    grupo_recorrencia_id=grupo_id,
                )
                db.session.add(reserva)
                db.session.flush()  # garante reserva.id para o bloqueio
                criar_bloqueios_automaticos(reserva)
                criadas += 1
            data_atual += timedelta(days=1)

        db.session.commit()
        registrar_log("criou_reserva_recorrente", "reserva", None,
                      f"Grupo {grupo_id}: {criadas} reservas na sala {sala_id}")
        flash(f"{criadas} reuniões recorrentes criadas com sucesso!", "sucesso")
        return redirect(url_for("colaborador.painel"))

    return render_template("reserva_recorrente.html", salas=salas)


@colaborador_bp.route("/recorrencia/<grupo_id>/cancelar", methods=["POST"])
@login_required
def cancelar_recorrencia(grupo_id):
    reservas = Reserva.query.filter(
        Reserva.grupo_recorrencia_id == grupo_id,
        Reserva.usuario_id == current_user.id,
        Reserva.status.in_(["confirmada", "em_andamento"]),
    ).all()

    if not reservas:
        abort(404)

    for reserva in reservas:
        reserva.status = "cancelada"
        remover_bloqueios_automaticos(reserva.id)

    db.session.commit()
    registrar_log("cancelou_recorrencia", "reserva", None,
                  f"Grupo {grupo_id}: {len(reservas)} reuniões canceladas por {current_user.nome}")
    flash(f"{len(reservas)} reuniões da recorrência foram canceladas.", "sucesso")
    return redirect(url_for("colaborador.painel"))


@colaborador_bp.route("/reserva/<int:reserva_id>/cancelar-individual", methods=["POST"])
@login_required
def cancelar_reserva_individual(reserva_id):
    """Cancela UMA ocorrência da recorrência sem afetar as demais."""
    reserva = db.get_or_404(Reserva, reserva_id)

    if reserva.usuario_id != current_user.id:
        abort(403)

    reserva.status = "cancelada"
    remover_bloqueios_automaticos(reserva.id)
    db.session.commit()

    registrar_log("cancelou_reserva", "reserva", reserva.id, f"Sala: {reserva.sala.nome}")
    notificar_reserva_cancelada(reserva)
    flash("Reunião cancelada.", "sucesso")
    return redirect(url_for("colaborador.painel"))


@colaborador_bp.route("/calendario")
@login_required
def calendario():
    return render_template("calendario.html")


@colaborador_bp.route("/api/eventos-calendario")
@login_required
def eventos_calendario():
    reservas = Reserva.query.filter(Reserva.status.in_(["confirmada", "em_andamento"])).all()

    eventos = [{
        "title": f"{r.titulo} ({r.sala.nome})",
        "start": r.inicio.isoformat(),
        "end": r.fim.isoformat(),
        "backgroundColor": r.sala.cor_fundo if "linear-gradient" not in r.sala.cor_fundo else "#3b82f6",
        "borderColor": r.sala.cor_fundo if "linear-gradient" not in r.sala.cor_fundo else "#3b82f6",
        "textColor": r.sala.cor_texto,
    } for r in reservas]

    return jsonify(eventos)

@colaborador_bp.route("/sala/<int:sala_id>/horarios")
@login_required
def horarios_sala(sala_id):
    sala = db.get_or_404(Sala, sala_id)

    reservas = Reserva.query.filter(
        Reserva.sala_id == sala_id,
        Reserva.status.in_(["confirmada", "em_andamento"])
    ).order_by(Reserva.inicio).all()

    return render_template("horarios_sala.html", sala=sala, reservas=reservas)



@colaborador_bp.route("/reserva/<int:reserva_id>/excluir", methods=["POST"])
@login_required
def excluir_minha_reserva(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)

    # Garante que o colaborador só pode excluir a própria reserva
    if reserva.usuario_id != current_user.id:
        abort(403)

    reserva.status = "cancelada"
    remover_bloqueios_automaticos(reserva.id)
    db.session.commit()

    registrar_log("cancelou_reserva", "reserva", reserva.id, f"Sala: {reserva.sala.nome}")
    notificar_reserva_cancelada(reserva)

    flash("Sua reunião foi cancelada.", "sucesso")
    return redirect(url_for("colaborador.painel"))


@colaborador_bp.route("/reserva/<int:reserva_id>/editar", methods=["GET", "POST"])
@login_required
def editar_minha_reserva(reserva_id):
    reserva = db.get_or_404(Reserva, reserva_id)

    if reserva.usuario_id != current_user.id:
        abort(403)

    salas = Sala.query.filter_by(ativa=True).all()

    if request.method == "POST":
        novo_titulo = request.form["titulo"].strip()
        novo_inicio = datetime.strptime(request.form["inicio"], "%Y-%m-%dT%H:%M")
        novo_fim = datetime.strptime(request.form["fim"], "%Y-%m-%dT%H:%M")
        nova_sala_id = int(request.form["sala_id"])

        if novo_fim <= novo_inicio:
            flash("O horário final deve ser depois do inicial.", "erro")
            return render_template("editar_reserva.html", reserva=reserva, salas=salas)

        disponivel, mensagem = horario_disponivel(
            nova_sala_id, novo_inicio, novo_fim, ignorar_reserva_id=reserva.id
        )
        if not disponivel:
            flash(mensagem, "erro")
            return render_template("editar_reserva.html", reserva=reserva, salas=salas)

        remover_bloqueios_automaticos(reserva.id)

        reserva.titulo = novo_titulo
        reserva.inicio = novo_inicio
        reserva.fim = novo_fim
        reserva.sala_id = nova_sala_id
        db.session.commit()

        criar_bloqueios_automaticos(reserva)

        registrar_log("editou_reserva", "reserva", reserva.id, f"Sala: {reserva.sala.nome}")
        flash("Reunião atualizada com sucesso.", "sucesso")
        return redirect(url_for("colaborador.painel"))

    return render_template("editar_reserva.html", reserva=reserva, salas=salas)