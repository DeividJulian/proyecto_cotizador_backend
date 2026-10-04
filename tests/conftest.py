import os

# IMPORTANTE: se fija ANTES de importar la app para que los tests nunca toquen la base real (Neon)
os.environ["DATABASE_URL"] = "sqlite:///./test_cotizador.db"

import pytest
from fastapi.testclient import TestClient

from database import Base, engine
from main import app

assert str(engine.url).startswith("sqlite"), "Los tests solo deben correr contra SQLite"

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
    yield


@pytest.fixture
def client():
    return TestClient(app)


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
