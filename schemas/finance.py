from pydantic import BaseModel, Field


class SimulationInput(BaseModel):
    hours_by_role: dict[str, float] = Field(min_length=1)
    margin_pct: float = Field(default=30.0, ge=0, le=200)
    contingency_pct: float = Field(default=10.0, ge=0, le=100)
    discount_pct: float = Field(default=0.0, ge=0, le=50)
    vat_pct: float = Field(default=19.0, ge=0, le=30)
