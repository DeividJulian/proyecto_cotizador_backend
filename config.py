"""Configuración leída de variables de entorno (archivo .env en local, panel de Render en producción)."""
import os
import secrets

from dotenv import load_dotenv

load_dotenv()

# Firma de los tokens de sesión. Sin SECRET_KEY se genera una al azar: las sesiones se pierden al reiniciar.
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
TOKEN_HORAS = int(os.getenv("TOKEN_HORAS", "72"))

# ID de cliente OAuth de Google (termina en .apps.googleusercontent.com). Es público: el front usa el mismo.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
