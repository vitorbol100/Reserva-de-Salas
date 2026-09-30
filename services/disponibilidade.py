from models import Sala, Reserva, BloqueioSala
from extensions import db
from services.auditoria import registrar_log


def salas_conflitantes(sala: Sala):
    ids = {sala.id}
    ids.update(sala.ids_vinculados())

    outras_salas = Sala.query.filter(Sala.id != sala.id).all()
    for outra in outras_salas:
        if sala.id in outra.ids_vinculados():
            ids.add(outra.id)

    return list(ids)


def horario_disponivel(sala_id, inicio, fim, ignorar_reserva_id=None):
    sala = db.session.get(Sala, sala_id)
    if not sala:
        return False, "Sala não encontrada."

    ids_para_checar = salas_conflitantes(sala)

    query_reservas = Reserva.query.filter(
        Reserva.sala_id.in_(ids_para_checar),
        Reserva.status.in_(["confirmada", "em_andamento"]),
        Reserva.inicio < fim,
    Reserva.fim > inicio,
    )
    if ignorar_reserva_id:
        query_reservas = query_reservas.filter(Reserva.id != ignorar_reserva_id)

    conflito = query_reservas.first()
    if conflito:
        return False, f"Conflito com a reserva '{conflito.titulo}' na sala {conflito.sala.nome}."

    conflito_bloqueio = BloqueioSala.query.filter(
        BloqueioSala.sala_id.in_(ids_para_checar),
        BloqueioSala.inicio < fim,
        BloqueioSala.fim > inicio,
    ).first()

    if conflito_bloqueio:
        return False, f"Sala bloqueada no período ({conflito_bloqueio.motivo or 'sem motivo informado'})."

    return True, "Disponível"


def criar_bloqueios_automaticos(reserva: Reserva):
    sala = db.session.get(Sala, reserva.sala_id)
    for sala_vinculada_id in sala.ids_vinculados()
        bloqueio = BloqueioSala(
    sala_id=sala_vinculada_id,
            inicio=reserva.inicio,
            fim=reserva.fim,
            motivo=f"Uso automático — {sala.nome} reservada",
            automatico=True,
            reserve_origem_id=reserva.id,
        )
        db.session.add(bloqueio)
    db.session.commit()


def remover_bloqueios_automaticos(reserva_id):
    BloqueioSala.query.filter_by(
        reserva_origem_id=reserva_id, automatico=True
    ).delete()
    db.session.commit()