from datetime import datetime
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


@colaborador_bp.route("/painel")
@login_required
def painel():
    salas = Sala.query.filter_by(ativa=True).all()
    minhas_reservas = Reserva.query.filter_by(
        usuario_id=current_user.id, status="confirmada" 
    ).order_by(Reserva.inicio).all()
    return render_template("dashboard.html", salas=salas, reservas=minhas_reservas)


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

        participantes_raw = request.form.get("participantes", "")
        emails_participantes = [
            email.strip()
            for email in participantes_raw.split(",")
            if email.strip()
        ]

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