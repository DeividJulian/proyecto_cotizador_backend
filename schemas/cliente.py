from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Corto = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


class ClienteCreate(BaseModel):
    nombre: Nombre
    empresa: Corto | None = None
    email: EmailStr
    telefono: Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None = None


class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    empresa: str | None
    email: str
    telefono: str | None
    creado_en: datetime
