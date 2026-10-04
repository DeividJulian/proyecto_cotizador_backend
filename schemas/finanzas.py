from pydantic import BaseModel, Field


class SimulacionEntrada(BaseModel):
    horas_por_rol: dict[str, float] = Field(min_length=1)
    margen_pct: float = Field(default=30.0, ge=0, le=200)
    contingencia_pct: float = Field(default=10.0, ge=0, le=100)
    descuento_pct: float = Field(default=0.0, ge=0, le=50)
    iva_pct: float = Field(default=19.0, ge=0, le=30)
