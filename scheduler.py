from apscheduler.schedulers.background import BackgroundScheduler
from services.status_reunioes import atualizar_status_reunioes, enviar_lembretes_pendentes


def iniciar_scheduler(app):
    scheduler = BackgroundScheduler()

    def rodar_com_contexto(funcao):
        def wrapper():
            with app.app_context():
                funcao()
        return wrapper

    scheduler.add_job(rodar_com_contexto(atualizar_status_reunioes), "interval", minutes=1)
    scheduler.add_job(rodar_com_contexto(enviar_lembretes_pendentes), "interval", minutes=1)
    scheduler.start()
    return scheduler