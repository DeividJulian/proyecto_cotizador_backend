"""Login sin contraseña: códigos de verificación de un solo uso por correo y tokens de sesión JWT."""
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
from models.cliente import Cliente
from models.usuario import CodigoVerificacion, Usuario
from services.correo import enviar_correo

ALGORITMO = "HS256"


class EsperaCodigo(Exception):
    def __init__(self, segundos: int):
        self.segundos = segundos
        super().__init__(f"Wait {segundos} seconds before requesting another code")


class CodigoInvalido(Exception):
    pass


def ahora() -> datetime:
    return datetime.now(timezone.utc)


def _con_zona(fecha: datetime) -> datetime:
    """SQLite devuelve las fechas sin zona horaria: se asumen en UTC."""
    return fecha if fecha.tzinfo else fecha.replace(tzinfo=timezone.utc)


def _hash(usuario_id: int, codigo: str) -> str:
    return hmac.new(config.SECRET_KEY.encode(), f"{usuario_id}:{codigo}".encode(), hashlib.sha256).hexdigest()


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def buscar_usuario(db: Session, email: str) -> Usuario | None:
    return db.query(Usuario).filter(func.lower(Usuario.email) == normalizar_email(email)).first()


def rol_inicial(email: str) -> str:
    return "admin" if normalizar_email(email) in config.ADMIN_EMAILS else "cliente"


def vincular_cliente(db: Session, usuario: Usuario) -> None:
    """Liga un usuario con rol cliente a su ficha de Cliente (la que usa el administrador para cotizarle)."""
    if usuario.rol != "cliente" or usuario.cliente_id is not None:
        return
    cliente = db.query(Cliente).filter(func.lower(Cliente.email) == normalizar_email(usuario.email)).first()
    if not cliente:
        cliente = Cliente(nombre=usuario.nombre, empresa=usuario.empresa, email=usuario.email)
        db.add(cliente)
        db.flush()
    usuario.cliente_id = cliente.id


def _ultimo_codigo(db: Session, usuario: Usuario, solo_activos: bool = False) -> CodigoVerificacion | None:
    consulta = db.query(CodigoVerificacion).filter(CodigoVerificacion.usuario_id == usuario.id)
    if solo_activos:
        consulta = consulta.filter(CodigoVerificacion.usado.is_(False))
    return consulta.order_by(CodigoVerificacion.id.desc()).first()


def emitir_codigo(db: Session, usuario: Usuario, proposito: str) -> str:
    """Genera un código nuevo e invalida los anteriores. Respeta una espera mínima entre envíos."""
    ultimo = _ultimo_codigo(db, usuario)
    if ultimo:
        espera = config.CODIGO_ESPERA_SEGUNDOS - (ahora() - _con_zona(ultimo.creado_en)).total_seconds()
        if espera > 0:
            raise EsperaCodigo(math.ceil(espera))

    db.query(CodigoVerificacion).filter(
        CodigoVerificacion.usuario_id == usuario.id, CodigoVerificacion.usado.is_(False)
    ).update({"usado": True})
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    db.add(
        CodigoVerificacion(
            usuario_id=usuario.id,
            codigo_hash=_hash(usuario.id, codigo),
            proposito=proposito,
            expira_en=ahora() + timedelta(minutes=config.CODIGO_MINUTOS),
        )
    )
    db.flush()
    return codigo


def verificar_codigo(db: Session, usuario: Usuario, codigo: str) -> None:
    """Valida el último código activo. Lanza CodigoInvalido; el llamador debe guardar el intento fallido."""
    registro = _ultimo_codigo(db, usuario, solo_activos=True)
    if not registro:
        raise CodigoInvalido("There is no active code: request a new one")
    if _con_zona(registro.expira_en) < ahora():
        registro.usado = True
        raise CodigoInvalido("The code expired: request a new one")
    if not hmac.compare_digest(registro.codigo_hash, _hash(usuario.id, codigo)):
        registro.intentos += 1
        restantes = config.CODIGO_INTENTOS - registro.intentos
        if restantes <= 0:
            registro.usado = True
            raise CodigoInvalido("Incorrect code. Too many attempts: request a new one")
        raise CodigoInvalido(f"Incorrect code. Attempts left: {restantes}")
    registro.usado = True


def enviar_codigo(usuario: Usuario, codigo: str, proposito: str) -> None:
    accion = "verify your account" if proposito == "registro" else "log in"
    asunto = "Your AI Quoter verification code" if proposito == "registro" else "Your AI Quoter login code"
    texto = (
        f"Hi {usuario.nombre},\n\n"
        f"Use this code to {accion}: {codigo}\n\n"
        f"It expires in {config.CODIGO_MINUTOS} minutes. If you did not request it, ignore this email.\n\n"
        "AI Quoter"
    )
    html = (
        f"<p>Hi {escape(usuario.nombre)},</p>"
        f"<p>Use this code to {accion}:</p>"
        f'<p style="font-size:28px;font-weight:700;letter-spacing:6px">{codigo}</p>'
        f"<p>It expires in {config.CODIGO_MINUTOS} minutes. If you did not request it, ignore this email.</p>"
        "<p>AI Quoter</p>"
    )
    enviar_correo(usuario.email, asunto, texto, html)


def crear_token(usuario: Usuario, horas: float | None = None) -> str:
    vence = ahora() + timedelta(hours=config.TOKEN_HORAS if horas is None else horas)
    return jwt.encode({"sub": str(usuario.id), "rol": usuario.rol, "exp": vence}, config.SECRET_KEY, algorithm=ALGORITMO)


def leer_token(token: str) -> int | None:
    """Devuelve el id del usuario del token, o None si es inválido o venció. El rol se lee siempre de la base."""
    try:
        return int(jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITMO])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
