"""Passwordless login: one-time verification codes by email and JWT session tokens."""
import hashlib
import hmac
import math
import secrets
from datetime import datetime, timedelta, timezone
from html import escape

import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

import config
from models.user import User, VerificationCode
from services.mailer import send_email
from services.rates import create_initial_rates

ALGORITHM = "HS256"


class CodeCooldown(Exception):
    def __init__(self, seconds: int):
        self.seconds = seconds
        super().__init__(f"Espera {seconds} segundos antes de pedir otro código")


class InvalidCode(Exception):
    pass


def now() -> datetime:
    return datetime.now(timezone.utc)


def _with_tz(value: datetime) -> datetime:
    """SQLite returns dates without a time zone: they are assumed to be UTC."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hash(user_id: int, code: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), f"{user_id}:{code}".encode(), hashlib.sha256).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def find_user(db: Session, email: str) -> User | None:
    return db.query(User).filter(func.lower(User.email) == normalize_email(email)).first()


def _last_code(db: Session, user: User, active_only: bool = False) -> VerificationCode | None:
    query = db.query(VerificationCode).filter(VerificationCode.user_id == user.id)
    if active_only:
        query = query.filter(VerificationCode.used.is_(False))
    return query.order_by(VerificationCode.id.desc()).first()


def issue_code(db: Session, user: User, purpose: str) -> str:
    """Creates a new code and invalidates the previous ones. Enforces a minimum wait between emails."""
    last = _last_code(db, user)
    if last:
        wait = config.CODE_WAIT_SECONDS - (now() - _with_tz(last.created_at)).total_seconds()
        if wait > 0:
            raise CodeCooldown(math.ceil(wait))

    db.query(VerificationCode).filter(VerificationCode.user_id == user.id, VerificationCode.used.is_(False)).update(
        {VerificationCode.used: True}
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        VerificationCode(
            user_id=user.id,
            code_hash=_hash(user.id, code),
            purpose=purpose,
            expires_at=now() + timedelta(minutes=config.CODE_MINUTES),
        )
    )
    db.flush()
    return code


def check_code(db: Session, user: User, code: str) -> None:
    """Validates the last active code. Raises InvalidCode; the caller must save the failed attempt."""
    record = _last_code(db, user, active_only=True)
    if not record:
        raise InvalidCode("No hay un código activo: pide uno nuevo")
    if _with_tz(record.expires_at) < now():
        record.used = True
        raise InvalidCode("El código venció: pide uno nuevo")
    if not hmac.compare_digest(record.code_hash, _hash(user.id, code)):
        record.attempts += 1
        left = config.CODE_ATTEMPTS - record.attempts
        if left <= 0:
            record.used = True
            raise InvalidCode("Código incorrecto. Agotaste los intentos: pide uno nuevo")
        raise InvalidCode(f"Código incorrecto. Te quedan {left} intentos")
    record.used = True


def complete_login(db: Session, user: User) -> None:
    """After a correct code: the first time the account is activated with the market rates."""
    if not user.verified:
        user.verified = True
        create_initial_rates(db, user)
    user.last_login_at = now()


def send_code(user: User, code: str, purpose: str) -> None:
    action = "verificar tu cuenta" if purpose == "register" else "iniciar sesión"
    subject = "Tu código de verificación de Cotizador IA" if purpose == "register" else "Tu código para entrar a Cotizador IA"
    text = (
        f"Hola {user.name}:\n\n"
        f"Usa este código para {action}: {code}\n\n"
        f"Vence en {config.CODE_MINUTES} minutos. Si no lo pediste, ignora este correo.\n\n"
        "Cotizador IA"
    )
    html = (
        f"<p>Hola {escape(user.name)}:</p>"
        f"<p>Usa este código para {action}:</p>"
        f'<p style="font-size:28px;font-weight:700;letter-spacing:6px">{code}</p>'
        f"<p>Vence en {config.CODE_MINUTES} minutos. Si no lo pediste, ignora este correo.</p>"
        "<p>Cotizador IA</p>"
    )
    send_email(user.email, subject, text, html)


def create_token(user: User, hours: float | None = None) -> str:
    expires = now() + timedelta(hours=config.TOKEN_HOURS if hours is None else hours)
    return jwt.encode({"sub": str(user.id), "exp": expires}, config.SECRET_KEY, algorithm=ALGORITHM)


def read_token(token: str) -> int | None:
    """Returns the user id of the token, or None when it is invalid or expired."""
    try:
        return int(jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
