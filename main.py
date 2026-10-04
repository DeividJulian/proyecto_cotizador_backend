import importlib
import pkgutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import models  # noqa: F401  (registra todas las tablas)
import routers
from database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Quotation Engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registra automáticamente cada archivo de la carpeta routers/ que defina `router`
for _, nombre_modulo, _ in pkgutil.iter_modules(routers.__path__):
    modulo = importlib.import_module(f"routers.{nombre_modulo}")
    if hasattr(modulo, "router"):
        app.include_router(modulo.router)


@app.get("/", tags=["System"])
def raiz():
    return {"mensaje": "AI Quotation Engine API is running"}


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
