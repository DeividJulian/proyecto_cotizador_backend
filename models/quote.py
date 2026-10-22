"""Quotes and their lines. The tables keep their original Spanish column names; the code uses English names."""
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


def now():
    return datetime.now(timezone.utc)


class Quote(Base):
    __tablename__ = "cotizaciones"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False, index=True)  # owner
    title = Column("titulo", String, nullable=False)
    client_name = Column("cliente_nombre", String, nullable=True)  # optional: who the project is for
    client_company = Column("cliente_empresa", String, nullable=True)
    scope_description = Column("descripcion_alcance", Text, nullable=False)
    status = Column("estado", String, nullable=False, default="draft")

    margin_pct = Column("margen_pct", Float, nullable=False, default=30.0)
    contingency_pct = Column("contingencia_pct", Float, nullable=False, default=10.0)
    discount_pct = Column("descuento_pct", Float, nullable=False, default=0.0)
    vat_pct = Column("iva_pct", Float, nullable=False, default=19.0)

    analysis = Column("analisis", JSON, nullable=False, default=dict)
    estimate = Column("estimacion", JSON, nullable=False, default=dict)
    financials = Column("financiero", JSON, nullable=False, default=dict)
    proposal = Column("propuesta", Text, nullable=True)
    total = Column(Integer, nullable=False, default=0)

    created_at = Column("creada_en", DateTime(timezone=True), nullable=False, default=now)
    updated_at = Column("actualizada_en", DateTime(timezone=True), nullable=False, default=now, onupdate=now)

    user = relationship("User")
    items = relationship("QuoteItem", cascade="all, delete-orphan", order_by="QuoteItem.id")


class QuoteItem(Base):
    """A line of the scope: a module detected by the analysis or an item added by hand."""

    __tablename__ = "items_cotizacion"

    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column("cotizacion_id", Integer, ForeignKey("cotizaciones.id"), nullable=False)
    name = Column("nombre", String, nullable=False)
    category = Column("categoria", String, nullable=False, default="Personalizado")
    complexity = Column("complejidad", String, nullable=False, default="medium")
    source = Column("origen", String, nullable=False, default="manual")  # "ai" or "manual"
    hours_optimistic = Column("horas_optimista", Float, nullable=False, default=0.0)
    hours_likely = Column("horas_probable", Float, nullable=False, default=0.0)
    hours_pessimistic = Column("horas_pesimista", Float, nullable=False, default=0.0)
    hours_expected = Column("horas_esperadas", Float, nullable=False, default=0.0)  # PERT average
    split = Column("distribucion", JSON, nullable=False, default=dict)  # role -> share of the hours
    reasons = Column("motivos", Text, nullable=False, default="")
