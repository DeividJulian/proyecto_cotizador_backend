from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=100)]
Codigo = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class RegistroEntrada(BaseModel):
    nombre: Nombre
    email: EmailStr


class LoginEntrada(BaseModel):
    email: EmailStr


class VerificarEntrada(BaseModel):
    email: EmailStr
    codigo: Codigo


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    creado_en: datetime
    ultimo_acceso: datetime | None


class SesionOut(BaseModel):
    token: str
    usuario: UsuarioOut
