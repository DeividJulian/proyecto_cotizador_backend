from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


def ahora():
    return datetime.now(timezone.utc)


class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    titulo = Column(String, nullable=False)
    descripcion_alcance = Column(Text, nullable=False)
    estado = Column(String, nullable=False, default="borrador")

    margen_pct = Column(Float, nullable=False, default=30.0)
    contingencia_pct = Column(Float, nullable=False, default=10.0)
    descuento_pct = Column(Float, nullable=False, default=0.0)
    iva_pct = Column(Float, nullable=False, default=19.0)

    analisis = Column(JSON, nullable=False, default=dict)
    estimacion = Column(JSON, nullable=False, default=dict)
    financiero = Column(JSON, nullable=False, default=dict)
    propuesta = Column(Text, nullable=True)
    total = Column(Integer, nullable=False, default=0)

    creada_en = Column(DateTime(timezone=True), nullable=False, default=ahora)
    actualizada_en = Column(DateTime(timezone=True), nullable=False, default=ahora, onupdate=ahora)

    cliente = relationship("Cliente")
    items = relationship("ItemCotizacion", cascade="all, delete-orphan", order_by="ItemCotizacion.id")


class ItemCotizacion(Base):
    """Una línea del alcance: un módulo detectado por la IA o un ítem agregado a mano."""

    __tablename__ = "items_cotizacion"

    id = Column(Integer, primary_key=True, index=True)
    cotizacion_id = Column(Integer, ForeignKey("cotizaciones.id"), nullable=False)
    nombre = Column(String, nullable=False)
    categoria = Column(String, nullable=False, default="Custom")
    complejidad = Column(String, nullable=False, default="media")
    origen = Column(String, nullable=False, default="manual")  # "ia" o "manual"
    horas_optimista = Column(Float, nullable=False, default=0.0)
    horas_probable = Column(Float, nullable=False, default=0.0)
    horas_pesimista = Column(Float, nullable=False, default=0.0)
    horas_esperadas = Column(Float, nullable=False, default=0.0)  # promedio PERT
    distribucion = Column(JSON, nullable=False, default=dict)  # rol -> fracción del total
    motivos = Column(Text, nullable=False, default="")
