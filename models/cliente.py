from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    empresa = Column(String, nullable=True)
    email = Column(String, unique=True, nullable=False)
    telefono = Column(String, nullable=True)
    creado_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
