from datetime import datetime
from extensions import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


class Usuario(db.Model, UserMixin):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    nivel = db.Column(db.String(20), nullable=False, default="colaborador")
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, senha_texto):
        self.senha_hash = generate_password_hash(senha_texto)

    def checar_senha(self, senha_texto):
        return check_password_hash(self.senha_hash, senha_texto)

    def __repr__(self):
        return f"<Usuario {self.email} ({self.nivel})>"


class Sala(db.Model):
    __tablename__ = "salas"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    capacidade = db.Column(db.Integer, nullable=False)
    salas_vinculadas = db.Column(db.String(50), nullable=True)
    ativa = db.Column(db.Boolean, default=True)

    # Cor de fundo (hex) e cor de destaque para exibição visual
    cor_fundo = db.Column(db.String(20), default="#e2e8f0")
    cor_texto = db.Column(db.String(20), default="#1e293b")

    def ids_vinculados(self):
        if not self.salas_vinculadas:
            return []
        return [int(i) for i in self.salas_vinculadas.split(",") if i]


class Reserva(db.Model):
    __tablename__ = "reservas"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(30), default="confirmada")

    quantidade_pessoas = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    sala_id = db.Column(db.Integer, db.ForeignKey("salas.id"), nullable=False)

    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    uid_calendario = db.Column(db.String(120), unique=True)

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        backref="reservas"
    )

    criado_por = db.relationship(
        "Usuario",
        foreign_keys=[criado_por_id]
    )

    sala = db.relationship("Sala", backref="reservas")


class BloqueioSala(db.Model):
    __tablename__ = "bloqueios_sala"

    id = db.Column(db.Integer, primary_key=True)
    sala_id = db.Column(db.Integer, db.ForeignKey("salas.id"), nullable=False)
    inicio = db.Column(db.DateTime, nullable=False)
    fim = db.Column(db.DateTime, nullable=False)
    motivo = db.Column(db.String(200), nullable=True)
    automatico = db.Column(db.Boolean, default=False)
    reserva_origem_id = db.Column(db.Integer, db.ForeignKey("reservas.id"), nullable=True)
    criado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)

    # recorrência
    recorrente = db.Column(db.Boolean, default=False)
    dias_semana = db.Column(db.String(20), nullable=True)  # ex: "0,2,4" (seg=0 ... dom=6)
    recorrencia_ate = db.Column(db.DateTime, nullable=True)
    grupo_recorrencia_id = db.Column(db.String(36), nullable=True)  # agrupa instâncias geradas

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    sala = db.relationship("Sala", foreign_keys=[sala_id])


class LogAuditoria(db.Model):
    __tablename__ = "logs_auditoria"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=True)
    acao = db.Column(db.String(50), nullable=False)  # criou_reserva, cancelou_reserva, moveu_reserva, bloqueou_sala, etc
    entidade = db.Column(db.String(50), nullable=False)  # reserva, bloqueio, usuario
    entidade_id = db.Column(db.Integer, nullable=True)
    detalhes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    usuario = db.relationship("Usuario")


class ParticipanteReserva(db.Model):
    __tablename__ = "participantes_reserva"

    id = db.Column(db.Integer, primary_key=True)
    reserva_id = db.Column(
        db.Integer,
        db.ForeignKey("reservas.id"),
        nullable=False
    )
    email = db.Column(db.String(200), nullable=False)
    nome = db.Column(db.String(200), nullable=True)

    reserva = db.relationship(
        "Reserva",
        backref=db.backref(
            "participantes",
            cascade="all, delete-orphan"
        )
    )
