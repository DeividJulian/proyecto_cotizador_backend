import importlib
import logging
import pkgutil
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import models  # noqa: F401  (registra todas las tablas)
import routers
from database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cotizador.api")

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


@app.middleware("http")
async def registrar_peticiones(request: Request, call_next):
    inicio = time.perf_counter()
    respuesta = await call_next(request)
    ms = (time.perf_counter() - inicio) * 1000
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, respuesta.status_code, ms)
    return respuesta


@app.exception_handler(RequestValidationError)
async def error_validacion(request: Request, exc: RequestValidationError):
    mensajes = []
    for e in exc.errors():
        campo = ".".join(str(x) for x in e["loc"] if x not in ("body", "query", "path"))
        mensajes.append(f"{campo}: {e['msg']}" if campo else e["msg"])
    logger.warning("Validation failed on %s %s: %s", request.method, request.url.path, mensajes)
    return JSONResponse(status_code=422, content={"detail": "; ".join(mensajes)})


@app.exception_handler(IntegrityError)
async def error_integridad(request: Request, exc: IntegrityError):
    logger.warning("Integrity violation on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=409, content={"detail": "The operation violates a database constraint"})


@app.exception_handler(SQLAlchemyError)
async def error_bd(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal database error"})


@app.get("/", tags=["System"])
def raiz():
    return {"mensaje": "AI Quotation Engine API is running"}


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok"}
