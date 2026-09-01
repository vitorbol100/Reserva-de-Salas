import uuid

from app import create_app
from extensions import db
from models import Reserva

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text(
                "ALTER TABLE reservas ADD COLUMN uid_calendario VARCHAR(120)"
            ))
            conn.commit()
            print("Coluna uid_calendario adicionada.")
        except Exception as e:
            print(f"Aviso: {e}")

    reservas_sem_uid = Reserva.query.filter(
        (Reserva.uid_calendario == None) | (Reserva.uid_calendario == "")
    ).all()

    for reserva in reservas_sem_uid:
        reserva.uid_calendario = str(uuid.uuid4())

    db.session.commit()
    print(f"{len(reservas_sem_uid)} reservas atualizadas com UID de calendário.")