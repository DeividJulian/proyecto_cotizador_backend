import os
import re

# IMPORTANT: set BEFORE importing the app so tests never touch the real database (Neon), never send real emails
# and never call a real AI provider
os.environ["DATABASE_URL"] = "sqlite:///./test_cotizador.db"
os.environ["EMAIL_BACKEND"] = "memory"
os.environ["SECRET_KEY"] = "clave-de-pruebas-con-al-menos-32-bytes-de-largo"
for name in ("AI_PROVIDER", "AI_API_KEY", "AI_MODEL", "AI_BASE_URL", "AI_FALLBACK_MODEL"):
    os.environ[name] = ""

import pytest
from fastapi.testclient import TestClient

from database import Base, engine
from main import app
from services.mailer import OUTBOX
from services.rates import MARKET_RATES

assert str(engine.url).startswith("sqlite"), "Tests must only run against SQLite"

SCOPE = (
    "Necesitamos una tienda en línea con catálogo de productos, carrito de compras y pagos en línea. "
    "Panel de administración para gestionar pedidos y reportes de ventas. Los clientes deben iniciar sesión."
)

# Every new account starts with the market rates
RATES = MARKET_RATES


def last_code(email: str) -> str:
    """6-digit code of the last email sent to that address (memory email backend)."""
    email_sent = next(e for e in reversed(OUTBOX) if e["to"] == email)
    return re.search(r"\b\d{6}\b", email_sent["text"]).group()


def log_in(email: str = "ana@pyme.com", name: str = "Ana Pérez") -> TestClient:
    """Registers and verifies an account through the real API; returns an HTTP client with its token."""
    session = TestClient(app)
    r = session.post("/auth/register", json={"name": name, "email": email})
    assert r.status_code == 201, r.text
    r = session.post("/auth/verify", json={"email": email, "code": last_code(email)})
    assert r.status_code == 200, r.text
    session.headers["Authorization"] = f"Bearer {r.json()['token']}"
    return session


def delete_rates(session: TestClient) -> None:
    for rate in session.get("/rates").json():
        assert session.delete(f"/rates/{rate['id']}").status_code == 200


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    OUTBOX.clear()
    yield


@pytest.fixture
def anonymous():
    return TestClient(app)


@pytest.fixture
def client():
    """HTTP client logged in as Ana: the business tests act as a normal user."""
    return log_in("ana@pyme.com", "Ana Pérez")


@pytest.fixture
def other():
    """A second user, to check that nobody sees another user's data."""
    return log_in("luis@otra.com", "Luis Gómez")


@pytest.fixture
def rates(client):
    """The market rates are already loaded when the account is activated."""
    assert {r["role"]: r["hourly_rate"] for r in client.get("/rates").json()} == RATES


@pytest.fixture
def quote(client):
    r = client.post(
        "/quotes",
        json={"title": "Tienda en línea", "scope_description": SCOPE, "client_name": "Ana Pérez",
              "client_company": "Pyme SAS"},
    )
    assert r.status_code == 201
    return r.json()


@pytest.fixture
def analyzed_quote(client, rates, quote):
    r = client.post(f"/quotes/{quote['id']}/analyze")
    assert r.status_code == 200, r.text
    return r.json()
