from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required
from models import Usuario
from flask import session

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and usuario.ativo and usuario.checar_senha(senha):
            login_user(usuario)
            if usuario.nivel == "administrador":
                return redirect(url_for("admin.painel"))
            elif usuario.nivel == "recepcionista":
                return redirect(url_for("recepcionista.painel"))
            else:
                return redirect(url_for("colaborador.painel"))

        flash("E-mail ou senha inválidos.", "erro")

    session.permanent = True
    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))