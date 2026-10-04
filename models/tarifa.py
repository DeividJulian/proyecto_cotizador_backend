from sqlalchemy import Column, Integer, String

from database import Base


class Tarifa(Base):
    """Costo por hora de cada rol del equipo, en pesos colombianos."""

    __tablename__ = "tarifas"

    id = Column(Integer, primary_key=True, index=True)
    rol = Column(String, unique=True, nullable=False)
    valor_hora = Column(Integer, nullable=False)
