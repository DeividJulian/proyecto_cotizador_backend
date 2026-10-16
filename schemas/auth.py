from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

from schemas.cliente import Corto, Nombre

Codigo = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]
Rol = Literal["admin", "cliente"]


class RegistroEntrada(BaseModel):
    nombre: Nombre
    empresa: Corto | None = None
    email: EmailStr


class LoginEntrada(BaseModel):
    email: EmailStr


class VerificarEntrada(BaseModel):
    email: EmailStr
    codigo: Codigo


class CambioRol(BaseModel):
    rol: Rol


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    empresa: str | None
    rol: str
    verificado: bool
    cliente_id: int | None
    creado_en: datetime
    ultimo_acceso: datetime | None


class SesionOut(BaseModel):
    token: str
    usuario: UsuarioOut
