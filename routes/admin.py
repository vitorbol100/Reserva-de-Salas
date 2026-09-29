from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from functools import wraps
from models import Usuario
from extensions import db
from services.auditoria import registrar_log

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def apenas_admin(f):
    @wraps(f)
    def decorador(*args, **kwargs):
        if current_user.nivel != "administrador":
            flash("Acesso restrito ao administrador.", "erro")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorador


@admin_bp.route("/painel")
@login_required
@apenas_admin
def painel():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("admin_usuarios.html", usuarios=usuarios)


@admin_bp.route("/usuario/novo", methods=["POST"])
@login_required
@apenas_admin
def criar_usuario():
    nome = request.form["nome"].strip()
    email = request.form["email"].strip().lower()
    senha = request.form["senha"]
    nivel = request.form["nivel"]  # colaborador, recepcionista, administrador

    if Usuario.query.filter_by(email=email).first():
        flash("Já existe um usuário com este e-mail.", "erro")
        return redirect(url_for("admin.painel"))

    novo_usuario = Usuario(nome=nome, email=email, nivel=nivel)
    novo_usuario.set_senha(senha)
    db.session.add(novo_usuario)
    db.session.commit()

    flash(f"Usuário {nome} criado com sucesso!", "sucesso")
    return redirect(url_for("admin.painel"))


@admin_bp.route("/usuario/<int:usuario_id>/nivel", methods=["POST"])
@login_required
@apenas_admin
def alterar_nivel(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.nivel = request.form["nivel"]
    db.session.commit()
    flash("Permissão atualizada.", "sucesso")
    return redirect(url_for("admin.painel"))


@admin_bp.route("/usuario/<int:usuario_id>/senha", methods=["POST"])
@login_required
@apenas_admin
def alterar_senha(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    senha = request.form.get("senha", "")
    confirmar = request.form.get("confirmar_senha", "")

    if len(senha) < 4:
        flash("A senha deve ter pelo menos 4 caracteres.", "erro")
        return redirect(url_for("admin.painel"))
    if senha != confirmar:
        flash("As senhas não coincidem.", "erro")
        return redirect(url_for("admin.painel"))

    usuario.set_senha(senha)
    db.session.commit()

    registrar_log("alterou_senha", "usuario", usuario.id, f"Senha do usuário {usuario.nome} alterada pelo admin")
    flash(f"Senha de {usuario.nome} alterada com sucesso!", "sucesso")
    return redirect(url_for("admin.painel"))


@admin_bp.route("/usuario/<int:usuario_id>/desativar", methods=["POST"])
@login_required
@apenas_admin
def desativar_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.ativo = not usuario.ativo
    db.session.commit()
    flash("Status do usuário atualizado.", "sucesso")
    return redirect(url_for("admin.painel"))
