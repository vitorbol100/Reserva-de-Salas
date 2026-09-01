from getpass import getpass

from app import create_app
from extensions import db
from models import Usuario


app = create_app()

with app.app_context():
    email = input("E-mail do administrador: ").strip().lower()
    nova_senha = getpass("Nova senha: ")
    confirmar_senha = getpass("Confirme a nova senha: ")

    if nova_senha != confirmar_senha:
        print("As senhas não coincidem.")
        raise SystemExit(1)

    if len(nova_senha) < 8:
        print("A senha deve ter pelo menos 8 caracteres.")
        raise SystemExit(1)

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario:
        print("Usuário não encontrado.")
        raise SystemExit(1)

    usuario.set_senha(nova_senha)
    db.session.commit()

    print("Senha alterada com sucesso.")