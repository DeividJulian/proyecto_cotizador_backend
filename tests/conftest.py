import json
import os

# IMPORTANTE: se fija ANTES de importar la app para que los tests nunca toquen la base real (Neon)
os.environ["DATABASE_URL"] = "sqlite:///./test_cotizador.db"
os.environ["SECRET_KEY"] = "clave-de-pruebas-con-al-menos-32-bytes-de-largo"
os.environ["GOOGLE_CLIENT_ID"] = "pruebas.apps.googleusercontent.com"

import pytest
from fastapi.testclient import TestClient

import services.auth as auth
from database import Base, engine
from main import app
from services.tarifas import TARIFAS_MERCADO

assert str(engine.url).startswith("sqlite"), "Los tests solo deben correr contra SQLite"

ALCANCE = (
    "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea. "
    "Panel de administración para gestionar pedidos y reportes de ventas. Los clientes deben iniciar sesión."
)

# Cada cuenta nueva arranca con las tarifas de mercado
TARIFAS = TARIFAS_MERCADO

PREFIJO = "google-prueba:"
VERIFICADOR_REAL = auth.verificar_token_google  # el fixture lo reemplaza; algunas pruebas lo usan directamente


def credencial(email: str, nombre: str = "Usuario de prueba", sub: str | None = None, verificado: bool = True) -> str:
    """Credencial falsa de Google: en las pruebas el verificador la decodifica en vez de llamar a Google."""
    datos = {"sub": sub or f"sub-{email}", "email": email, "email_verified": verificado, "name": nombre,
             "picture": "https://foto.example.com/a.png"}
    return PREFIJO + json.dumps(datos)


def verificador_de_prueba(valor: str) -> dict:
    if not valor.startswith(PREFIJO):
        raise auth.TokenGoogleInvalido("Invalid token")
    return json.loads(valor[len(PREFIJO):])


def entrar(email: str = "ana@pyme.com", nombre: str = "Ana Pérez") -> TestClient:
    """Inicia sesión con el flujo real del API (POST /auth/google) y devuelve un cliente HTTP con su token."""
    sesion = TestClient(app)
    r = sesion.post("/auth/google", json={"credencial": credencial(email, nombre)})
    assert r.status_code == 200, r.text
    sesion.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return sesion


def borrar_tarifas(sesion: TestClient) -> None:
    for t in sesion.get("/tarifas").json():
        assert sesion.delete(f"/tarifas/{t['id']}").status_code == 200


@pytest.fixture(autouse=True)
def base_limpia(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(auth, "verificar_token_google", verificador_de_prueba)
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
    """Las tarifas de mercado ya vienen cargadas al crear la cuenta."""
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
