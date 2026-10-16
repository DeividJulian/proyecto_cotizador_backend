from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

CredencialGoogle = Annotated[str, StringConstraints(strip_whitespace=True, min_length=20, max_length=5000)]


class LoginGoogle(BaseModel):
    credencial: CredencialGoogle  # ID token que entrega el botón "Continuar con Google"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    foto_url: str | None
    creado_en: datetime
    ultimo_acceso: datetime | None


class SesionOut(BaseModel):
    token: str
    usuario: UsuarioOut
