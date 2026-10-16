from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from schemas.auth import LoginEntrada, RegistroEntrada, SesionOut, UsuarioOut, VerificarEntrada
from seguridad import usuario_actual
from services.auth import (
    CodigoInvalido,
    EsperaCodigo,
    ahora,
    buscar_usuario,
    crear_token,
    emitir_codigo,
    enviar_codigo,
    normalizar_email,
    rol_inicial,
    verificar_codigo,
    vincular_cliente,
)
from services.correo import ErrorCorreo

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _enviar_codigo(db: Session, usuario: Usuario, proposito: str) -> None:
    """Genera y envía el código. Si el correo no sale, deshace todo (no queda un usuario a medias)."""
    try:
        codigo = emitir_codigo(db, usuario, proposito)
    except EsperaCodigo as e:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(e))
    try:
        enviar_codigo(usuario, codigo, proposito)
    except ErrorCorreo:
        db.rollback()
        raise HTTPException(status_code=502, detail="We could not send the email. Try again in a few minutes.")
    db.commit()


@router.post("/registro", status_code=201)
def registro(datos: RegistroEntrada, db: Session = Depends(get_db)):
    """Creates the account and emails a verification code. If it was never verified, the code is resent."""
    usuario = buscar_usuario(db, datos.email)
    if usuario and usuario.verificado:
        raise HTTPException(status_code=409, detail="An account with that email already exists: log in")
    if usuario:
        usuario.nombre, usuario.empresa = datos.nombre, datos.empresa
    else:
        usuario = Usuario(
            nombre=datos.nombre,
            empresa=datos.empresa,
            email=normalizar_email(datos.email),
            rol=rol_inicial(datos.email),
        )
        db.add(usuario)
        db.flush()
    _enviar_codigo(db, usuario, "registro")
    return {"mensaje": "We sent a verification code to your email", "email": usuario.email}


@router.post("/login")
def login(datos: LoginEntrada, db: Session = Depends(get_db)):
    """Emails a one-time login code."""
    usuario = buscar_usuario(db, datos.email)
    if not usuario:
        raise HTTPException(status_code=404, detail="There is no account with that email: sign up first")
    _enviar_codigo(db, usuario, "login")
    return {"mensaje": "We sent a login code to your email", "email": usuario.email}


@router.post("/verificar", response_model=SesionOut)
def verificar(datos: VerificarEntrada, db: Session = Depends(get_db)):
    """Checks the emailed code and returns the session token."""
    usuario = buscar_usuario(db, datos.email)
    if not usuario:
        raise HTTPException(status_code=400, detail="There is no active code: request a new one")
    try:
        verificar_codigo(db, usuario, datos.codigo)
    except CodigoInvalido as e:
        db.commit()  # guarda el intento fallido o el código invalidado
        raise HTTPException(status_code=400, detail=str(e))
    usuario.verificado = True
    usuario.ultimo_acceso = ahora()
    vincular_cliente(db, usuario)
    db.commit()
    db.refresh(usuario)
    return {"token": crear_token(usuario), "usuario": usuario}


@router.get("/me", response_model=UsuarioOut)
def perfil(usuario: Usuario = Depends(usuario_actual)):
    return usuario
