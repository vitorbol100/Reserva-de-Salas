import uuid
from datetime import timedelta
from models import BloqueioSala
from extensions import db


def criar_bloqueio_recorrente(sala_id, hora_inicio, hora_fim, dias_semana, data_ate, motivo, criado_por_id):
    """
    Cria múltiplos bloqueios repetidos conforme dias da semana selecionados,
    até a data limite informada.

    dias_semana: lista de inteiros, 0=segunda ... 6=domingo
    hora_inicio / hora_fim: objetos datetime já com data do primeiro dia (usa-se apenas o horário)
    """
    grupo_id = str(uuid.uuid4())
    data_atual = hora_inicio.date()
    hora_ini = hora_inicio.time()
    hora_fim_t = hora_fim.time()

    bloqueios_criados = []

    while data_atual <= data_ate.date():
        if data_atual.weekday() in dias_semana:
            inicio_dia = _combinar(data_atual, hora_ini)
            fim_dia = _combinar(data_atual, hora_fim_t)

            bloqueio = BloqueioSala(
                sala_id=sala_id,
                inicio=inicio_dia,
                fim=fim_dia,
                motivo=motivo,
                automatico=False,
                recorrente=True,
                dias_semana=",".join(str(d) for d in dias_semana),
                recorrencia_ate=data_ate,
                grupo_recorrencia_id=grupo_id,
                criado_por_id=criado_por_id,
            )
            db.session.add(bloqueio)
            bloqueios_criados.append(bloqueio)

        data_atual += timedelta(days=1)

    db.session.commit()
    return bloqueios_criados, grupo_id


def _combinar(data, hora):
    from datetime import datetime
    return datetime.combine(data, hora)


def remover_grupo_recorrencia(grupo_id):
    BloqueioSala.query.filter_by(grupo_recorrencia_id=grupo_id).delete()
    db.session.commit()