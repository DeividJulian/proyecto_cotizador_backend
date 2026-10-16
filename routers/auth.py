from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import services.auth as auth
from database import get_db
from models.usuario import Usuario
from schemas.auth import LoginGoogle, SesionOut, UsuarioOut
from seguridad import usuario_actual

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/google", response_model=SesionOut)
def login_google(datos: LoginGoogle, db: Session = Depends(get_db)):
    """Exchanges the Google ID token for an app session. The first login creates the account with market rates."""
    try:
        datos_google = auth.verificar_token_google(datos.credencial)
        usuario = auth.entrar_con_google(db, datos_google)
    except auth.GoogleNoConfigurado:
        raise HTTPException(status_code=503, detail="Google login is not configured on the server")
    except auth.GoogleNoDisponible:
        raise HTTPException(status_code=503, detail="Could not contact Google: try again in a moment")
    except auth.TokenGoogleInvalido:
        raise HTTPException(status_code=401, detail="Google could not verify your account: try again")
    return {"token": auth.crear_token(usuario), "usuario": usuario}


@router.get("/me", response_model=UsuarioOut)
def perfil(usuario: Usuario = Depends(usuario_actual)):
    return usuario
