import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "Falta DATABASE_URL. Crea el archivo .env (puedes copiar .env.example) "
        "con una línea como: DATABASE_URL=postgresql+psycopg://usuario:clave@host/base?sslmode=require"
    )

opciones = {"pool_pre_ping": True, "pool_recycle": 300}  # Neon duerme la base tras 5 min sin uso
if DATABASE_URL.startswith("postgresql"):
    # Compatible con el conector "pooled" de Neon (PgBouncer): evita sentencias preparadas
    opciones["connect_args"] = {"prepare_threshold": None}

engine = create_engine(DATABASE_URL, **opciones)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
