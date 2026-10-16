from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    """Cuenta para entrar a la app. Rol "admin" (gestiona todo) o "cliente" (ve sus cotizaciones)."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)  # siempre en minúsculas
    empresa = Column(String, nullable=True)
    rol = Column(String, nullable=False, default="cliente")
    verificado = Column(Boolean, nullable=False, default=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)  # ficha de cliente del usuario
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)

    cliente = relationship("Cliente")


class CodigoVerificacion(Base):
    """Código de 6 dígitos enviado por correo. Se guarda solo su hash y es de un solo uso."""

    __tablename__ = "codigos_verificacion"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    codigo_hash = Column(String, nullable=False)
    proposito = Column(String, nullable=False)  # "registro" o "login"
    expira_en = Column(DateTime(timezone=True), nullable=False)
    intentos = Column(Integer, nullable=False, default=0)
    usado = Column(Boolean, nullable=False, default=False)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
