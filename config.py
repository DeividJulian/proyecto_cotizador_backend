"""Configuración leída de variables de entorno (archivo .env en local, panel de Render en producción)."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()


def _lista(valor: str | None) -> set[str]:
    return {e.strip().lower() for e in (valor or "").split(",") if e.strip()}


# Firma de los tokens de sesión. Sin SECRET_KEY se genera una al azar: las sesiones se pierden al reiniciar.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
TOKEN_HORAS = int(os.getenv("TOKEN_HORAS", "12"))

# Códigos de verificación enviados por correo
CODIGO_MINUTOS = int(os.getenv("CODIGO_MINUTOS", "10"))
CODIGO_INTENTOS = int(os.getenv("CODIGO_INTENTOS", "5"))
CODIGO_ESPERA_SEGUNDOS = int(os.getenv("CODIGO_ESPERA_SEGUNDOS", "30"))

# Correos que reciben el rol de administrador al registrarse (separados por comas)
ADMIN_EMAILS = _lista(os.getenv("ADMIN_EMAILS"))

# Envío de correos: consola | memoria | smtp | brevo
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "consola").strip().lower()
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@cotizador.local")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "AI Quoter")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
