from app import create_app
from extensions import db

app = create_app()

with app.app_context():
    with db.engine.connect() as conn:
        try:
            conn.execute(db.text("ALTER TABLE salas ADD COLUMN cor_fundo VARCHAR(20) DEFAULT '#e2e8f0'"))
            conn.execute(db.text("ALTER TABLE salas ADD COLUMN cor_texto VARCHAR(20) DEFAULT '#1e293b'"))
            conn.commit()
            print("Colunas adicionadas com sucesso.")
        except Exception as e:
            print(f"Aviso: {e}")