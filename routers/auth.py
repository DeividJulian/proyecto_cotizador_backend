from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.auth import CodeSent, LoginInput, PasswordLoginInput, RegisterInput, SessionOut, UserOut, VerifyInput
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
    now,
    send_code,
)
from services.demo import check_password, ensure_demo_accounts, is_demo_email
from services.mailer import EmailError

router = APIRouter(prefix="/auth", tags=["Autenticación"], responses=errors(400, 401, 404, 409, 422, 429, 502))


DEMO_NO_CODE = "Esta es la cuenta de demostración: entra con la opción «Con contraseña»"
WRONG_PASSWORD = (
    "Correo o contraseña incorrectos. La contraseña solo sirve para la cuenta de demostración; "
    "las demás cuentas entran con un código al correo."
)


def _send_code(db: Session, user: User, purpose: str) -> None:
    """Creates and sends the code. If the email does not go out, everything is undone (no half-created user)."""
    if is_demo_email(user.email):
        db.rollback()  # that inbox is not ours: no code is created or sent
        raise HTTPException(status_code=409, detail=DEMO_NO_CODE)
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
    if is_demo_email(data.email):
        raise HTTPException(status_code=409, detail=DEMO_NO_CODE)
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


@router.post("/password", response_model=SessionOut, summary="Entrar con contraseña (cuenta de demostración)")
def password_login(data: PasswordLoginInput, db: Session = Depends(get_db)):
    """Solo para la cuenta de demostración (DEMO_ACCOUNTS=true). Las demás cuentas entran con código al correo."""
    if not check_password(data.email, data.password):
        raise HTTPException(status_code=401, detail=WRONG_PASSWORD)
    user = find_user(db, data.email)
    if user is None:  # the database was emptied after the server started
        ensure_demo_accounts(db)
        user = find_user(db, data.email)
    user.last_login_at = now()
    db.commit()
    db.refresh(user)
    return {"token": create_token(user), "user": user}


@router.get("/me", response_model=UserOut, summary="Usuario actual")
def current_account(user: User = Depends(current_user)):
    return user
