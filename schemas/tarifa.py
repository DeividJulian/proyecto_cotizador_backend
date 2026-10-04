from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Rol = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=60)]


class TarifaCreate(BaseModel):
    rol: Rol
    valor_hora: int = Field(gt=0, le=2_000_000)


class TarifaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rol: str
    valor_hora: int
