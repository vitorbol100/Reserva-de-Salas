from datetime import datetime, timedelta
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from functools import wraps
from models import LogAuditoria
from services.relatorios import calcular_taxa_ocupacao

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")


def apenas_admin_ou_recepcionista(f):
    from flask import redirect, url_for, flash
    from functools import wraps

    @wraps(f)
    def decorador(*args, **kwargs):
        if current_user.nivel not in ("administrador", "recepcionista"):
            flash("Acesso não autorizado.", "erro")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorador


@relatorios_bp.route("/ocupacao")
@login_required
@apenas_admin_ou_recepcionista
def ocupacao():
    data_inicio_str = request.args.get("data_inicio")
    data_fim_str = request.args.get("data_fim")

    if data_inicio_str and data_fim_str:
        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d")
        data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d")
    else:
        data_fim = datetime.utcnow()
        data_inicio = data_fim - timedelta(days=30)

    dados = calcular_taxa_ocupacao(data_inicio, data_fim)
    return render_template(
        "relatorio_ocupacao.html",
        dados=dados,
        data_inicio=data_inicio.strftime("%Y-%m-%d"),
        data_fim=data_fim.strftime("%Y-%m-%d"),
    )


@relatorios_bp.route("/auditoria")
@login_required
@apenas_admin_ou_recepcionista
def auditoria():
    logs = LogAuditoria.query.order_by(LogAuditoria.criado_em.desc()).limit(200).all()
    return render_template("logs_auditoria.html", logs=logs)