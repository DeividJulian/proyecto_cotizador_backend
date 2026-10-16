from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Usuario(Base):
    """Cuenta creada al entrar con Google. Cada usuario ve y edita solo sus cotizaciones y tarifas."""

    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, nullable=False)  # id estable de la cuenta de Google
    email = Column(String, unique=True, nullable=False)  # siempre en minúsculas
    nombre = Column(String, nullable=False)
    foto_url = Column(String, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
    ultimo_acceso = Column(DateTime(timezone=True), nullable=True)
