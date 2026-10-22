"""Accounts and their login codes. The tables keep their original Spanish column names."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from database import Base


def now():
    return datetime.now(timezone.utc)


class User(Base):
    """Account to log in with an emailed code. Every user sees and edits only their own quotes and rates."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column("nombre", String, nullable=False)
    email = Column(String, unique=True, nullable=False)  # always lower case
    verified = Column("verificado", Boolean, nullable=False, default=False)
    created_at = Column("creado_en", DateTime(timezone=True), nullable=False, default=now)
    last_login_at = Column("ultimo_acceso", DateTime(timezone=True), nullable=True)


class VerificationCode(Base):
    """6-digit code sent by email. Only its hash is stored and it can be used once."""

    __tablename__ = "codigos_verificacion"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    code_hash = Column("codigo_hash", String, nullable=False)
    purpose = Column("proposito", String, nullable=False)  # "register" or "login"
    expires_at = Column("expira_en", DateTime(timezone=True), nullable=False)
    attempts = Column("intentos", Integer, nullable=False, default=0)
    used = Column("usado", Boolean, nullable=False, default=False)
    created_at = Column("creado_en", DateTime(timezone=True), nullable=False, default=now)
