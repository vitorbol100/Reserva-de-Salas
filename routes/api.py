from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.disponibilidade import horario_disponivel
from services.relatorios import sugerir_sala_por_capacidade

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/verificar-disponibilidade")
@login_required
def verificar_disponibilidade():
    sala_id = request.args.get("sala_id", type=int)
    inicio_str = request.args.get("inicio")
    fim_str = request.args.get("fim")

    if not all([sala_id, inicio_str, fim_str]):
        return jsonify({"disponivel": False, "mensagem": "Parâmetros incompletos."}), 400

    try:
        inicio = datetime.strptime(inicio_str, "%Y-%m-%dT%H:%M")
        fim = datetime.strptime(fim_str, "%Y-%m-%dT%H:%M")
    except ValueError:
        return jsonify({"disponivel": False, "mensagem": "Formato de data inválido."}), 400

    if fim <= inicio:
        return jsonify({"disponivel": False, "mensagem": "Horário final deve ser após o inicial."})

    disponivel, mensagem = horario_disponivel(sala_id, inicio, fim)
    return jsonify({"disponivel": disponivel, "mensagem": mensagem})


@api_bp.route("/sugerir-sala")
@login_required
def sugerir_sala():
    participantes = request.args.get("participantes", type=int)
    if not participantes:
        return jsonify({"salas": []})

    salas = sugerir_sala_por_capacidade(participantes)
    return jsonify({
        "salas": [{"id": s.id, "nome": s.nome, "capacidade": s.capacidade} for s in salas]
    })