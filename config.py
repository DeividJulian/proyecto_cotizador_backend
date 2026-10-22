"""Settings read from environment variables (.env file locally, Render dashboard in production).

The variable names stay as they were (TOKEN_HORAS, CODIGO_*) so existing deployments keep working.
"""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

# Signs the session tokens. Without SECRET_KEY a random one is generated: sessions are lost on restart.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
TOKEN_HOURS = int(os.getenv("TOKEN_HORAS", "72"))

# One-time codes sent by email
CODE_MINUTES = int(os.getenv("CODIGO_MINUTOS", "10"))
CODE_ATTEMPTS = int(os.getenv("CODIGO_INTENTOS", "5"))
CODE_WAIT_SECONDS = int(os.getenv("CODIGO_ESPERA_SEGUNDOS", "30"))

# Email delivery: console | memory | smtp | brevo (the Spanish names consola / memoria also work)
_EMAIL_ALIASES = {"consola": "console", "memoria": "memory"}
_backend = os.getenv("EMAIL_BACKEND", "console").strip().lower()
EMAIL_BACKEND = _EMAIL_ALIASES.get(_backend, _backend)
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@cotizador.local")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Cotizador IA")
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

# Browser origins allowed to call the API (comma separated). The Vercel front and local development.
CORS_ORIGINS = [
    o.strip().rstrip("/")
    for o in os.getenv(
        "CORS_ORIGINS", "https://cotizador-front-eight.vercel.app,http://localhost:4200,http://127.0.0.1:4200"
    ).split(",")
    if o.strip()
]
