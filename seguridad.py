"""Dependencia de FastAPI que exige una sesión iniciada."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from services.auth import leer_token

bearer = HTTPBearer(auto_error=False, description="Token from /auth/google")


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="You must log in", headers={"WWW-Authenticate": "Bearer"})
    usuario_id = leer_token(credenciales.credentials)
    usuario = db.get(Usuario, usuario_id) if usuario_id is not None else None
    if usuario is None:
        raise HTTPException(
            status_code=401, detail="Session expired or invalid: log in again", headers={"WWW-Authenticate": "Bearer"}
        )
    return usuario
