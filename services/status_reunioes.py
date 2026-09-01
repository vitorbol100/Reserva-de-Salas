from datetime import datetime
from models import Reserva
from extensions import db


def atualizar_status_reunioes():
    """Deve ser chamado periodicamente (via scheduler) para atualizar
    reservas confirmadas para 'em_andamento' ou 'concluida' conforme o horário atual."""
    agora = datetime.utcnow()

    em_andamento = Reserva.query.filter(
        Reserva.status == "confirmada",
        Reserva.inicio <= agora,
        Reserva.fim > agora,
    ).all()
    for r in em_andamento:
        r.status = "em_andamento"

    concluidas = Reserva.query.filter(
        Reserva.status.in_(["confirmada", "em_andamento"]),
        Reserva.fim <= agora,
    ).all()
    for r in concluidas:
        r.status = "concluida"

    db.session.commit()


def enviar_lembretes_pendentes():
    """Envia lembrete 15 minutos antes da reunião começar."""
    from datetime import timedelta
    from services.notificacoes import notificar_lembrete

    agora = datetime.utcnow()
    janela = agora + timedelta(minutes=15)

    reservas = Reserva.query.filter(
        Reserva.status == "confirmada",
        Reserva.lembrete_enviado == False,
        Reserva.inicio <= janela,
        Reserva.inicio > agora,
    ).all()

    for r in reservas:
        notificar_lembrete(r)
        r.lembrete_enviado = True

    db.session.commit()
