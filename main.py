import importlib
import logging
import pkgutil
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

import config
import models  # noqa: F401  (registers every table)
import routers
from database import Base, engine
from rpc.simulation import simulation_app
from schemas.common import Health, Message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cotizador.api")

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Cotizador IA",
    description="Convierte la descripción de un proyecto de software en una cotización: módulos, horas PERT, "
    "precio y propuesta comercial.",
    version="2.0.0",
    # operationId = the Python function name (listQuotes, not list_quotes_quotes_get): it names the generated client
    generate_unique_id_function=lambda route: route.name,
)

# Only the front (Vercel and local development) may call the API from a browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    # The front reads it to tell how long to wait when the AI usage limit is reached
    expose_headers=["Retry-After"],
)

# Registers every module of routers/ that defines `router`
for _, module_name, _ in pkgutil.iter_modules(routers.__path__):
    module = importlib.import_module(f"routers.{module_name}")
    if hasattr(module, "router"):
        app.include_router(module.router)

# gRPC (Connect protocol) on the same service and port: POST /cotizador.v1.SimulationService/Simulate.
# Render terminates TLS and talks HTTP/1.1 to the app; Connect works over HTTP/1.1, including server streaming.
app.mount(simulation_app.path, simulation_app)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code, ms)
    # Lets the front read the real transfer size in the browser's Resource Timing (REST vs gRPC comparison)
    origin = request.headers.get("origin")
    if origin in config.CORS_ORIGINS:
        response.headers["Timing-Allow-Origin"] = origin
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    messages = []
    for e in exc.errors():
        field = ".".join(str(x) for x in e["loc"] if x not in ("body", "query", "path"))
        messages.append(f"{field}: {e['msg']}" if field else e["msg"])
    logger.warning("Validation failed on %s %s: %s", request.method, request.url.path, messages)
    return JSONResponse(status_code=422, content={"detail": "Datos inválidos. " + "; ".join(messages)})


@app.exception_handler(IntegrityError)
async def integrity_error(request: Request, exc: IntegrityError):
    logger.warning("Integrity violation on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=409, content={"detail": "La operación viola una restricción de la base de datos"})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno de la base de datos"})


@app.get("/", response_model=Message, tags=["Sistema"], summary="Inicio")
def root():
    return {"message": "API del Cotizador IA funcionando"}


@app.get("/health", response_model=Health, tags=["Sistema"], summary="Estado")
def health():
    return {"status": "ok"}
