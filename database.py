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

options = {"pool_pre_ping": True, "pool_recycle": 300}  # Neon puts the database to sleep after 5 idle minutes
if DATABASE_URL.startswith("postgresql"):
    # Works with Neon's pooled connection (PgBouncer): no prepared statements
    options["connect_args"] = {"prepare_threshold": None}

engine = create_engine(DATABASE_URL, **options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
