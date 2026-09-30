"""Adiciona a coluna grupo_recorrencia_id na tabela reservas.

Necessário para a feature de reserva recorrente do colaborador.
Execute UMA vez após git pull:

    python migrar_grupo_recorrencia.py
"""
from app import create_app
from extensions import db
from sqlalchemy import text


def migrar():
    app = create_app()
    with app.app_context():
        # verifica se a coluna já existe
        resultado = db.session.execute(
            text("PRAGMA table_info(reservas)")
        ).fetchall()
        colunas = [linha[1] for linha in resultado]

        if "grupo_recorrencia_id" in colunas:
            print("Coluna grupo_recorrencia_id já existe. Nada a fazer.")
        else:
            db.session.execute(
                text("ALTER TABLE reservas ADD COLUMN grupo_recorrencia_id VARCHAR(36)")
            )
            db.session.commit()
            print("Coluna grupo_recorrencia_id adicionada com sucesso!")


if __name__ == "__main__":
    migrar()