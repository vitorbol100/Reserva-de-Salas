from datetime import datetime


def escapar_ics(valor):
    return (
        str(valor or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def gerar_ics(reserva):
    organizador_email = "victor@conebel.com.br"
    organizador_nome = "Sistema de Salas"

    uid = f"{reserva.uid_calendario}@sistemasalas.conebel.com.br"
    agora = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    inicio = reserva.inicio.strftime("%Y%m%dT%H%M%S")
    fim = reserva.fim.strftime("%Y%m%dT%H%M%S")

    titulo = escapar_ics(reserva.titulo)
    sala = escapar_ics(reserva.sala.nome)

    descricao = (
        "Reuniao agendada no Sistema de Salas.\\n"
        f"Sala: {sala}\\n"
        f"Titulo: {titulo}"
    )

    linhas_participantes = []

    linhas_participantes.append(
        f"ATTENDEE;CN={escapar_ics(reserva.usuario.nome)};"
        f"RSVP=TRUE:mailto:{reserva.usuario.email}"
    )

    for participante in getattr(reserva, "participantes", []):
        nome = escapar_ics(participante.nome or participante.email)
        linhas_participantes.append(
            f"ATTENDEE;CN={nome};RSVP=TRUE:mailto:{participante.email}"
        )

    bloco_participantes = "\n".join(linhas_participantes)

    conteudo = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Sistema de Salas//Conebel//PT-BR
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{agora}
DTSTART:{inicio}
DTEND:{fim}
SUMMARY:{titulo}
DESCRIPTION:{descricao}
LOCATION:{sala}
ORGANIZER;CN={organizador_nome}:mailto:{organizador_email}
{bloco_participantes}
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Lembrete de reuniao
END:VALARM
END:VEVENT
END:VCALENDAR
"""

    return conteudo.replace("\n", "\r\n")