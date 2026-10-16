"""Envío de correos. El proveedor se elige con EMAIL_BACKEND:

- consola: escribe el correo en la terminal (desarrollo local, no envía nada).
- memoria: lo guarda en BANDEJA (pruebas automáticas).
- smtp: servidor SMTP, por ejemplo Gmail con contraseña de aplicación.
- brevo: API HTTP de Brevo. Sirve en Render, cuyo plan gratis bloquea los puertos SMTP.
"""
import json
import logging
import smtplib
import urllib.request
from email.message import EmailMessage

import config

logger = logging.getLogger("cotizador.correo")

BANDEJA: list[dict] = []
BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class ErrorCorreo(Exception):
    """El proveedor no aceptó el correo (credenciales, red, remitente no verificado...)."""


def enviar_correo(destino: str, asunto: str, texto: str, html: str | None = None) -> None:
    backend = config.EMAIL_BACKEND
    if backend == "memoria":
        BANDEJA.append({"para": destino, "asunto": asunto, "texto": texto, "html": html})
        return
    if backend == "consola":
        logger.info("Correo para %s | %s\n%s", destino, asunto, texto)
        return

    enviadores = {"smtp": _enviar_smtp, "brevo": _enviar_brevo}
    if backend not in enviadores:
        raise ErrorCorreo(f"EMAIL_BACKEND desconocido: {backend}")
    try:
        enviadores[backend](destino, asunto, texto, html)
    except ErrorCorreo:
        raise
    except Exception as e:
        logger.error("No se pudo enviar el correo a %s con %s", destino, backend, exc_info=e)
        raise ErrorCorreo(str(e)) from e


def _enviar_smtp(destino: str, asunto: str, texto: str, html: str | None) -> None:
    mensaje = EmailMessage()
    mensaje["From"] = f"{config.EMAIL_FROM_NAME} <{config.EMAIL_FROM}>"
    mensaje["To"] = destino
    mensaje["Subject"] = asunto
    mensaje.set_content(texto)
    if html:
        mensaje.add_alternative(html, subtype="html")
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as servidor:
        servidor.starttls()
        if config.SMTP_USER:
            servidor.login(config.SMTP_USER, config.SMTP_PASSWORD)
        servidor.send_message(mensaje)


def _enviar_brevo(destino: str, asunto: str, texto: str, html: str | None) -> None:
    if not config.BREVO_API_KEY:
        raise ErrorCorreo("Falta BREVO_API_KEY")
    cuerpo = {
        "sender": {"name": config.EMAIL_FROM_NAME, "email": config.EMAIL_FROM},
        "to": [{"email": destino}],
        "subject": asunto,
        "textContent": texto,
    }
    if html:
        cuerpo["htmlContent"] = html
    peticion = urllib.request.Request(
        BREVO_URL,
        data=json.dumps(cuerpo).encode("utf-8"),
        headers={"api-key": config.BREVO_API_KEY, "Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    # urlopen lanza HTTPError si Brevo responde 4xx/5xx
    with urllib.request.urlopen(peticion, timeout=15):
        pass
