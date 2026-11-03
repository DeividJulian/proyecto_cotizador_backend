from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import CodeSent, LoginInput, RegisterInput, SessionOut, UserOut, VerifyInput
from schemas.common import errors
from security import current_user
from services.auth import (
    CodeCooldown,
    InvalidCode,
    check_code,
    complete_login,
    create_token,
    find_user,
    issue_code,
    normalize_email,
    send_code,
)
from services.mailer import EmailError

router = APIRouter(prefix="/auth", tags=["Autenticación"], responses=errors(400, 401, 404, 409, 422, 429, 502))


def _send_code(db: Session, user: User, purpose: str) -> None:
    """Creates and sends the code. If the email does not go out, everything is undone (no half-created user)."""
    try:
        code = issue_code(db, user, purpose)
    except CodeCooldown as e:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(e))
    try:
        send_code(user, code, purpose)
    except EmailError:
        db.rollback()
        raise HTTPException(status_code=502, detail="No pudimos enviar el correo. Intenta de nuevo en unos minutos.")
    db.commit()


@router.post("/register", response_model=CodeSent, status_code=201, summary="Crear cuenta")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    """Crea la cuenta y envía un código de verificación al correo. Si nunca se verificó, reenvía el código."""
    user = find_user(db, data.email)
    if user and user.verified:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo: inicia sesión")
    if user:
        user.name = data.name
    else:
        user = User(name=data.name, email=normalize_email(data.email))
        db.add(user)
        db.flush()
    _send_code(db, user, "register")
    return {"message": "Te enviamos un código de verificación al correo", "email": user.email}


@router.post("/login", response_model=CodeSent, summary="Pedir código para entrar")
def login(data: LoginInput, db: Session = Depends(get_db)):
    """Envía un código de un solo uso al correo."""
    user = find_user(db, data.email)
    if not user:
        raise HTTPException(status_code=404, detail="No hay ninguna cuenta con ese correo: regístrate primero")
    _send_code(db, user, "login")
    return {"message": "Te enviamos un código para entrar", "email": user.email}


@router.post("/verify", response_model=SessionOut, summary="Verificar código")
def verify(data: VerifyInput, db: Session = Depends(get_db)):
    """Valida el código del correo y devuelve el token de sesión. La primera vez activa la cuenta."""
    user = find_user(db, data.email)
    if not user:
        raise HTTPException(status_code=400, detail="No hay un código activo: pide uno nuevo")
    try:
        check_code(db, user, data.code)
    except InvalidCode as e:
        db.commit()  # saves the failed attempt or the invalidated code
        raise HTTPException(status_code=400, detail=str(e))
    complete_login(db, user)
    db.commit()
    db.refresh(user)
    return {"token": create_token(user), "user": user}


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def me(user: User = Depends(current_user)):
    return user
