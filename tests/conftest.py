import os
import re

# IMPORTANTE: se fija ANTES de importar la app para que los tests nunca toquen la base real (Neon)
# ni envíen correos de verdad
os.environ["DATABASE_URL"] = "sqlite:///./test_cotizador.db"
os.environ["EMAIL_BACKEND"] = "memoria"
os.environ["SECRET_KEY"] = "clave-de-pruebas-con-al-menos-32-bytes-de-largo"

import pytest
from fastapi.testclient import TestClient

from database import Base, engine
from main import app
from services.correo import BANDEJA
from services.tarifas import TARIFAS_MERCADO

assert str(engine.url).startswith("sqlite"), "Los tests solo deben correr contra SQLite"

ALCANCE = (
    "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea. "
    "Panel de administración para gestionar pedidos y reportes de ventas. Los clientes deben iniciar sesión."
)

# Cada cuenta nueva arranca con las tarifas de mercado
TARIFAS = TARIFAS_MERCADO


def ultimo_codigo(email: str) -> str:
    """Código de 6 dígitos del último correo enviado a ese email (backend de correo "memoria")."""
    correo = next(c for c in reversed(BANDEJA) if c["para"] == email)
    return re.search(r"\b\d{6}\b", correo["texto"]).group()


def entrar(email: str = "ana@pyme.com", nombre: str = "Ana Pérez") -> TestClient:
    """Registra y verifica una cuenta con el flujo real del API; devuelve un cliente HTTP con su token."""
    sesion = TestClient(app)
    r = sesion.post("/auth/registro", json={"nombre": nombre, "email": email})
    assert r.status_code == 201, r.text
    r = sesion.post("/auth/verificar", json={"email": email, "codigo": ultimo_codigo(email)})
    assert r.status_code == 200, r.text
    sesion.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return sesion


def borrar_tarifas(sesion: TestClient) -> None:
    for t in sesion.get("/tarifas").json():
        assert sesion.delete(f"/tarifas/{t['id']}").status_code == 200


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
    """Cliente HTTP con la sesión de Ana: las pruebas de negocio actúan como un usuario normal."""
    return entrar("ana@pyme.com", "Ana Pérez")


@pytest.fixture
def otro():
    """Un segundo usuario, para comprobar que nadie ve los datos de otro."""
    return entrar("luis@otra.com", "Luis Gómez")


@pytest.fixture
def tarifas(client):
    """Las tarifas de mercado ya vienen cargadas al activar la cuenta."""
    assert {t["rol"]: t["valor_hora"] for t in client.get("/tarifas").json()} == TARIFAS


@pytest.fixture
def cotizacion(client):
    r = client.post(
        "/cotizaciones",
        json={"titulo": "Tienda en línea", "descripcion_alcance": ALCANCE, "cliente_nombre": "Ana Pérez",
              "cliente_empresa": "Pyme SAS"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def cotizacion_analizada(client, tarifas, cotizacion):
    r = client.post(f"/cotizaciones/{cotizacion['id']}/analizar")
    assert r.status_code == 200, r.text
    return r.json()
