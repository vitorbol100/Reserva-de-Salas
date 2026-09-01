from app import create_app
from services.notificacoes import enviar_email

app = create_app()

with app.app_context():
    enviar_email(
        destinatario="victor@conebel.com.br",
        assunto="Teste do Sistema de Salas",
        corpo_html="""
        <h3>Teste de envio</h3>
        <p>Este e-mail foi enviado pelo sistema.</p>
        """
    )