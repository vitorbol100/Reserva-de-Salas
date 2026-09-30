from flask import Flask
from flask_login import LoginManager
from config import Config
from extensions import db, login_manager
from models import Usuario, Sala

from routes.auth import auth_bp
from routes.colaborador import colaborador_bp
from routes.recepcionista import recepcionista_bp
from routes.admin import admin_bp
from scheduler import iniciar_scheduler
from routes.relatorios import relatorios_bp
from routes.api import api_bp
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, redirect, url_for
from flask_login import current_user

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(colaborador_bp)
    app.register_blueprint(recepcionista_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(relatorios_bp)

    @app.route("/")
    def inicio():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        if current_user.nivel == "administrador":
            return redirect(url_for("admin.painel"))

        if current_user.nivel == "recepcionista":
            return redirect(url_for("recepcionista.painel"))

        return redirect(url_for("colaborador.painel"))

    with app.app_context():
        db.create_all()
        seed_salas()
        seed_admin_inicial()

    return app


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def seed_salas():
    if Sala.query.first():
        return

    antarctica = Sala(nome="Sala Antarctica", capacidade=11, cor_fundo="#3b82f6", cor_texto="#ffffff")
    skol = Sala(nome="Sala Skol", capacidade=10, cor_fundo="#facc15", cor_texto="#1e293b")
    bud = Sala(nome="Sala Bud", capacidade=5, cor_fundo="#ef4444", cor_texto="#ffffff")
    auditorio = Sala(nome="Auditório", capacidade=150, cor_fundo="#e5e7eb", cor_texto="#1e293b")
    auditorio_brahma = Sala(nome="Auditório Brahma", capacidade=50, cor_fundo="#dc2626", cor_texto="#ffffff")

    db.session.add_all([antarctica, skol, bud, auditorio, auditorio_brahma])
    db.session.flush()

    ambev = Sala(
        nome="Sala Ambev",
        capacidade=21,
        salas_vinculadas=f"{antarctica.id},{skol.id}",
        cor_fundo="linear-gradient(135deg, #3b82f6 50%, #ffffff 50%)",
        cor_texto="#1e293b",
    )
    db.session.add(ambev)
    db.session.commit()


def seed_admin_inicial():
    """Cria um administrador padrão apenas se não existir nenhum usuário."""
    if Usuario.query.first():
        return

    admin = Usuario(
        nome="Administrador Geral",
        email="admin@conebel.com.br",
        nivel="administrador",
    )
    admin.set_senha("C0n32677")  # trocar no primeiro acesso
    db.session.add(admin)
    db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=False
    )