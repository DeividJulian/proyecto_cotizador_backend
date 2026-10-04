from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from schemas.alcance import TextoAlcance

Titulo = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=150)]
Estado = Literal["borrador", "enviada", "aceptada", "rechazada"]
Complejidad = Literal["baja", "media", "alta"]


class CotizacionCreate(BaseModel):
    cliente_id: int
    titulo: Titulo
    descripcion_alcance: TextoAlcance
    margen_pct: float = Field(default=30.0, ge=0, le=200)
    contingencia_pct: float = Field(default=10.0, ge=0, le=100)
    descuento_pct: float = Field(default=0.0, ge=0, le=50)
    iva_pct: float = Field(default=19.0, ge=0, le=30)


class CotizacionUpdate(BaseModel):
    titulo: Titulo | None = None
    descripcion_alcance: TextoAlcance | None = None
    margen_pct: float | None = Field(default=None, ge=0, le=200)
    contingencia_pct: float | None = Field(default=None, ge=0, le=100)
    descuento_pct: float | None = Field(default=None, ge=0, le=50)
    iva_pct: float | None = Field(default=None, ge=0, le=30)


class CambioEstado(BaseModel):
    estado: Estado


class ItemCreate(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
    categoria: Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)] = "Custom"
    complejidad: Complejidad = "media"
    horas_probable: float = Field(gt=0, le=5000)
    distribucion: dict[str, float] | None = None


class ItemUpdate(BaseModel):
    nombre: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)] | None = None
    complejidad: Complejidad | None = None
    horas_probable: float | None = Field(default=None, gt=0, le=5000)
    distribucion: dict[str, float] | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    categoria: str
    complejidad: str
    origen: str
    horas_optimista: float
    horas_probable: float
    horas_pesimista: float
    horas_esperadas: float
    distribucion: dict
    motivos: str


class CotizacionResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    titulo: str
    estado: str
    total: int
    creada_en: datetime
    actualizada_en: datetime


class CotizacionOut(CotizacionResumen):
    descripcion_alcance: str
    margen_pct: float
    contingencia_pct: float
    descuento_pct: float
    iva_pct: float
    analisis: dict
    estimacion: dict
    financiero: dict
    propuesta: str | None
    items: list[ItemOut]
