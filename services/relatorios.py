from datetime import datetime
from models import Reserva, Sala
from extensions import db
from sqlalchemy import func


def calcular_taxa_ocupacao(data_inicio, data_fim):
    """
    Calcula a taxa de ocupação (%) de cada sala no período informado,
    baseado no total de horas reservadas vs. horas disponíveis
    (considerando expediente de 10h/dia úteis, ajustável).
    """
    HORAS_EXPEDIENTE_POR_DIA = 10
    dias_periodo = (data_fim.date() - data_inicio.date()).days + 1
    horas_disponiveis_totais = dias_periodo * HORAS_EXPEDIENTE_POR_DIA

    salas = Sala.query.filter_by(ativa=True).all()
    resultado = []

    for sala in salas:
        reservas = Reserva.query.filter(
            Reserva.sala_id == sala.id,
            Reserva.status.in_(["confirmada", "concluida", "em_andamento"]),
            Reserva.inicio >= data_inicio,
            Reserva.inicio <= data_fim,
        ).all()

        total_horas_usadas = sum(
            (r.fim - r.inicio).total_seconds() / 3600 for r in reservas
        )

        taxa = (total_horas_usadas / horas_disponiveis_totais * 100) if horas_disponiveis_totais else 0

        resultado.append({
            "sala": sala.nome,
            "capacidade": sala.capacidade,
            "total_reservas": len(reservas),
            "horas_usadas": round(total_horas_usadas, 1),
            "taxa_ocupacao": round(taxa, 1),
        })

    resultado.sort(key=lambda x: x["taxa_ocupacao"], reverse=True)
    return resultado


def sugerir_sala_por_capacidade(numero_participantes):
    """Retorna salas ordenadas pela menor capacidade que ainda atenda ao número de participantes."""
    salas_adequadas = Sala.query.filter(
        Sala.ativa == True,
        Sala.capacidade >= numero_participantes
    ).order_by(Sala.capacidade.asc()).all()

    return salas_adequadas