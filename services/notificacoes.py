import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from flask import current_app

from services.calendario_ics import gerar_ics


def enviar_email(
    destinatario,
    assunto,
    corpo_html,
    anexo_ics=None,
    metodo_ics="REQUEST",
):
    destinatario = str(destinatario or "").strip()
    assunto = str(assunto or "").strip()

    smtp_host = current_app.config.get("SMTP_HOST")
    smtp_port = int(current_app.config.get("SMTP_PORT", 587))
    smtp_user = str(current_app.config.get("SMTP_USER") or "").strip()
    smtp_senha = current_app.config.get("SMTP_SENHA")

    if not destinatario or "@" not in destinatario:
        raise ValueError(f"Destinatário inválido: {destinatario!r}")

    if not smtp_host or not smtp_user or not smtp_senha:
        print(f"[EMAIL SIMULADO] Para: {destinatario}")
        print(f"[EMAIL SIMULADO] Assunto: {assunto}")
        return False

    mensagem = EmailMessage()

    mensagem["Subject"] = assunto
    mensagem["From"] = formataddr(
        ("Sistema de Salas", smtp_user)
    )
    mensagem["To"] = destinatario

    mensagem.set_content(
        "Sua reunião foi agendada. "
        "Abra este e-mail em um cliente compatível com calendário."
    )

    mensagem.add_alternative(
        corpo_html,
        subtype="html",
    )

    if anexo_ics:
        mensagem.add_attachment(
            anexo_ics.encode("utf-8"),
            maintype="text",
            subtype="calendar",
            filename="convite.ics",
        )

    print("From:", mensagem["From"])
    print("To:", mensagem["To"])
    print("Destinatários detectados:", mensagem.get_all("To"))

    try:
        with smtplib.SMTP(
            smtp_host,
            smtp_port,
            timeout=30,
        ) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.ehlo()
            servidor.login(smtp_user, smtp_senha)

            servidor.send_message(
                mensagem,
                from_addr=smtp_user,
                to_addrs=[destinatario],
            )

        print(f"[EMAIL ENVIADO] Para: {destinatario}")
        return True

    except smtplib.SMTPException as erro:
        print(f"[ERRO SMTP] Falha no envio: {erro}")
        raise


def notificar_reserva_criada(reserva):
    corpo = f"""
    <h3>Reunião agendada</h3>
    <p><b>Sala:</b> {reserva.sala.nome}</p>
    <p><b>Título:</b> {reserva.titulo}</p>
    <p><b>Início:</b> {reserva.inicio.strftime('%d/%m/%Y %H:%M')}</p>
    <p><b>Fim:</b> {reserva.fim.strftime('%d/%m/%Y %H:%M')}</p>
    <p>O convite de calendário está anexado a este e-mail.</p>
    """

    convite = gerar_ics(reserva)

    destinatarios = [reserva.usuario.email]
    for participante in getattr(reserva, "participantes", []):
        destinatarios.append(participante.email)

    for destinatario in destinatarios:
        enviar_email(
            destinatario=destinatario,
            assunto="Reunião agendada com sucesso",
            corpo_html=corpo,
            anexo_ics=convite,
            metodo_ics="REQUEST",
        )


def notificar_reserva_cancelada(reserva):
    corpo = f"""
    <h3>Reunião cancelada</h3>
    <p><b>Sala:</b> {reserva.sala.nome}</p>
    <p><b>Título:</b> {reserva.titulo}</p>
    <p><b>Horário original:</b>
       {reserva.inicio.strftime('%d/%m/%Y %H:%M')}
       -
       {reserva.fim.strftime('%H:%M')}
    </p>
    """

    convite = gerar_ics(reserva)
    convite = convite.replace(
        "METHOD:REQUEST",
        "METHOD:CANCEL",
    ).replace(
        "STATUS:CONFIRMED",
        "STATUS:CANCELLED",
    )

    return enviar_email(
        destinatario=reserva.usuario.email,
        assunto="Reunião cancelada",
        corpo_html=corpo,
        anexo_ics=convite,
        metodo_ics="CANCEL",
    )


def notificar_reserva_movida(reserva, sala_antiga_nome):
    corpo = f"""
    <h3>Sua reunião foi movida de sala</h3>
    <p><b>De:</b> {sala_antiga_nome}</p>
    <p><b>Para:</b> {reserva.sala.nome}</p>
    <p><b>Horário:</b>
       {reserva.inicio.strftime('%d/%m/%Y %H:%M')}
       -
       {reserva.fim.strftime('%H:%M')}
    </p>
    """

    convite = gerar_ics(reserva)

    return enviar_email(
        destinatario=reserva.usuario.email,
        assunto="Sua reunião foi movida de sala",
        corpo_html=corpo,
        anexo_ics=convite,
        metodo_ics="REQUEST",
    )


def notificar_lembrete(reserva):
    corpo = f"""
    <h3>Lembrete de reunião</h3>
    <p>
        Sua reunião <b>{reserva.titulo}</b>
        começa em 15 minutos.
    </p>
    <p><b>Sala:</b> {reserva.sala.nome}</p>
    <p><b>Horário:</b>
       {reserva.inicio.strftime('%H:%M')}
       -
       {reserva.fim.strftime('%H:%M')}
    </p>
    """

    return enviar_email(
        destinatario=reserva.usuario.email,
        assunto="Lembrete: sua reunião começa em breve",
        corpo_html=corpo,
    )