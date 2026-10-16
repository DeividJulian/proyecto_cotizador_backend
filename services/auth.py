"""Inicio de sesión con Google y tokens de sesión JWT propios de la app."""
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import func
from sqlalchemy.orm import Session

import config
from models.usuario import Usuario
from services.tarifas import crear_tarifas_iniciales

ALGORITMO = "HS256"
EMISORES_GOOGLE = {"accounts.google.com", "https://accounts.google.com"}


class GoogleNoConfigurado(Exception):
    pass


class TokenGoogleInvalido(Exception):
    pass


class GoogleNoDisponible(Exception):
    """No se pudieron descargar las llaves públicas de Google (red caída o timeout)."""


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def verificar_token_google(credencial: str) -> dict:
    """Valida el ID token que entrega el botón de Google (firma, audiencia, emisor y vencimiento).

    Devuelve sus datos: sub, email, email_verified, name, picture. Las pruebas reemplazan esta función.
    """
    if not config.GOOGLE_CLIENT_ID:
        raise GoogleNoConfigurado("GOOGLE_CLIENT_ID is not configured")
    from google.auth.exceptions import GoogleAuthError
    from google.auth.transport import requests as google_requests
    from google.oauth2 import id_token

    try:
        datos = id_token.verify_oauth2_token(credencial, google_requests.Request(), config.GOOGLE_CLIENT_ID)
    except ValueError as e:  # firma, audiencia o vencimiento inválidos
        raise TokenGoogleInvalido(str(e)) from e
    except GoogleAuthError as e:  # no se pudo hablar con Google
        raise GoogleNoDisponible(str(e)) from e
    if datos.get("iss") not in EMISORES_GOOGLE:
        raise TokenGoogleInvalido("Unexpected issuer")
    return datos


def entrar_con_google(db: Session, datos: dict) -> Usuario:
    """Busca o crea la cuenta a partir de los datos verificados de Google. Al crearla carga tarifas de mercado."""
    if not datos.get("email") or not datos.get("email_verified"):
        raise TokenGoogleInvalido("The Google account has no verified email")
    sub = str(datos["sub"])
    email = datos["email"].strip().lower()
    nombre = (datos.get("name") or email.split("@")[0]).strip()

    usuario = db.query(Usuario).filter(Usuario.google_sub == sub).first()
    if usuario is None:
        usuario = db.query(Usuario).filter(func.lower(Usuario.email) == email).first()
        if usuario is not None:
            usuario.google_sub = sub
    if usuario is None:
        usuario = Usuario(google_sub=sub, email=email, nombre=nombre)
        db.add(usuario)
        db.flush()
        crear_tarifas_iniciales(db, usuario)

    usuario.email = email
    usuario.nombre = nombre
    usuario.foto_url = datos.get("picture")
    usuario.ultimo_acceso = ahora()
    db.commit()
    db.refresh(usuario)
    return usuario


def crear_token(usuario: Usuario, horas: float | None = None) -> str:
    vence = ahora() + timedelta(hours=config.TOKEN_HORAS if horas is None else horas)
    return jwt.encode({"sub": str(usuario.id), "exp": vence}, config.SECRET_KEY, algorithm=ALGORITMO)


def leer_token(token: str) -> int | None:
    """Devuelve el id del usuario del token, o None si es inválido o venció."""
    try:
        return int(jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITMO])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
