from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from database import Base


class Tarifa(Base):
    """Costo por hora de cada rol del equipo, en pesos colombianos. Cada usuario tiene las suyas."""

    __tablename__ = "tarifas"
    __table_args__ = (UniqueConstraint("usuario_id", "rol", name="uq_tarifa_usuario_rol"),)

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    rol = Column(String, nullable=False)
    valor_hora = Column(Integer, nullable=False)
