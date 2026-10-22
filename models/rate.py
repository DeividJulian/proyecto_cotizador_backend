from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from database import Base


class Rate(Base):
    """Hourly cost of each team role, in Colombian pesos. Every user has their own."""

    __tablename__ = "tarifas"
    # Column names as stored in the database
    __table_args__ = (UniqueConstraint("usuario_id", "rol", name="uq_tarifa_usuario_rol"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    role = Column("rol", String, nullable=False)
    hourly_rate = Column("valor_hora", Integer, nullable=False)
