from models import LogAuditoria
from extensions import db
from flask_login import current_user


def registrar_log(acao, entidade, entidade_id=None, detalhes=None):
    """Registra uma ação no histórico de auditoria."""
    usuario_id = current_user.id if current_user and current_user.is_authenticated else None

    log = LogAuditoria(
        usuario_id=usuario_id,
        acao=acao,
        entidade=entidade,
        entidade_id=entidade_id,
        detalhes=detalhes,
    )
    db.session.add(log)
    db.session.commit()