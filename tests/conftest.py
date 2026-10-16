import os
import re

# IMPORTANTE: se fija ANTES de importar la app para que los tests nunca toquen la base real (Neon)
# ni envíen correos de verdad
os.environ["DATABASE_URL"] = "sqlite:///./test_cotizador.db"
os.environ["EMAIL_BACKEND"] = "memoria"
os.environ["SECRET_KEY"] = "clave-de-pruebas-con-al-menos-32-bytes-de-largo"
os.environ["ADMIN_EMAILS"] = "admin@cotizador-pruebas.com"

import pytest
from fastapi.testclient import TestClient

from database import Base, engine
from main import app
from services.correo import BANDEJA

assert str(engine.url).startswith("sqlite"), "Los tests solo deben correr contra SQLite"

ADMIN_EMAIL = "admin@cotizador-pruebas.com"


def ultimo_codigo(email: str) -> str:
    """Código de 6 dígitos del último correo enviado a ese email (backend de correo "memoria")."""
    correo = next(c for c in reversed(BANDEJA) if c["para"] == email)
    return re.search(r"\b\d{6}\b", correo["texto"]).group()


def entrar(email: str, nombre: str = "Usuario de prueba", empresa: str | None = None) -> TestClient:
    """Registra y verifica una cuenta con el flujo real del API; devuelve un cliente HTTP con su token."""
    sesion = TestClient(app)
    r = sesion.post("/auth/registro", json={"nombre": nombre, "email": email, "empresa": empresa})
    assert r.status_code == 201, r.text
    r = sesion.post("/auth/verificar", json={"email": email, "codigo": ultimo_codigo(email)})
    assert r.status_code == 200, r.text
    sesion.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return sesion

ALCANCE = (
    "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea. "
    "Panel de administración para gestionar pedidos y reportes de ventas. Los clientes deben iniciar sesión."
)

TARIFAS = {"Backend": 55000, "Frontend": 50000, "UX/UI Design": 45000, "QA": 40000, "DevOps": 60000,
           "Project Management": 65000}


@pytest.fixture(autouse=True)
def base_limpia():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    BANDEJA.clear()
    yield


@pytest.fixture
def anonimo():
    return TestClient(app)


@pytest.fixture
def client():
    """Cliente HTTP con sesión de administrador (las pruebas de negocio actúan como admin)."""
    return entrar(ADMIN_EMAIL, "Administrador")


@pytest.fixture
def tarifas(client):
    for rol, valor in TARIFAS.items():
        assert client.post("/tarifas", json={"rol": rol, "valor_hora": valor}).status_code == 201


@pytest.fixture
def cliente_id(client):
    r = client.post("/clientes", json={"nombre": "Ana Pérez", "empresa": "Pyme SAS", "email": "ana@pyme.com"})
    assert r.status_code == 201
    return r.json()["id"]


@pytest.fixture
def cotizacion(client, cliente_id):
    r = client.post("/cotizaciones", json={"cliente_id": cliente_id, "titulo": "Tienda en línea", "descripcion_alcance": ALCANCE})
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def cotizacion_analizada(client, tarifas, cotizacion):
    r = client.post(f"/cotizaciones/{cotizacion['id']}/analizar")
    assert r.status_code == 200, r.text
    return r.json()
