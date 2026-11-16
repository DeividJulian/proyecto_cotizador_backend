"""Demo account (DEMO_ACCOUNTS): password login only for it, nothing is ever emailed to it."""
import pytest
from fastapi.testclient import TestClient

import config
from database import SessionLocal
from main import app
from services.demo import ensure_demo_accounts
from services.mailer import OUTBOX

DEMO = "administrador@gmail.com"


@pytest.fixture
def demo():
    """The account the server creates on start (the tests empty the database before each one)."""
    with SessionLocal() as db:
        ensure_demo_accounts(db)


def password_login(client, email=DEMO, password="demo123"):
    return client.post("/auth/password", json={"email": email, "password": password})


def test_default_settings():
    assert config.DEMO_ACCOUNTS is True
    assert config.DEMO_ADMIN_EMAIL == DEMO
    assert config.DEMO_PASSWORD == "demo123"


def test_demo_account_logs_in_and_sees_its_data(anonymous, demo):
    r = password_login(anonymous)
    assert r.status_code == 200, r.text
    session = TestClient(app, headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert session.get("/auth/me").json()["email"] == DEMO
    quotes = session.get("/quotes").json()
    assert len(quotes) == 4  # the example quotes, with every status
    assert {q["status"] for q in quotes} == {"draft", "sent", "accepted", "rejected"}
    assert len(session.get("/rates").json()) == 6
    assert session.get("/stats").json()["total_quotes"] == 4


def test_demo_account_is_created_once(demo):
    with SessionLocal() as db:
        ensure_demo_accounts(db)  # a second start does not duplicate anything
    session = TestClient(app, headers={"Authorization": f"Bearer {password_login(TestClient(app)).json()['token']}"})
    assert len(session.get("/quotes").json()) == 4


def test_email_is_not_case_sensitive(anonymous, demo):
    assert password_login(anonymous, email="Administrador@Gmail.com").status_code == 200


def test_wrong_password_is_rejected(anonymous, demo):
    r = password_login(anonymous, password="demo1234")
    assert r.status_code == 401
    assert "Correo o contraseña incorrectos" in r.json()["detail"]


def test_other_accounts_do_not_accept_the_password(anonymous, client, demo):
    """client is a normal account (logged in by code): the demo password does not open it."""
    assert password_login(anonymous, email="ana@pyme.com").status_code == 401
    assert password_login(anonymous, email="nadie@pyme.com").status_code == 401


def test_nothing_is_ever_emailed_to_the_demo_address(anonymous, demo):
    OUTBOX.clear()
    assert anonymous.post("/auth/login", json={"email": DEMO}).status_code == 409
    r = anonymous.post("/auth/register", json={"name": "Alguien", "email": DEMO})
    assert r.status_code == 409 and "Con contraseña" in r.json()["detail"]
    password_login(anonymous)
    assert OUTBOX == []


def test_the_mailer_also_refuses_the_demo_address():
    from services.mailer import send_email

    OUTBOX.clear()
    send_email(DEMO, "Prueba", "no debe salir")
    assert OUTBOX == []


def test_disabled_demo_accounts_cannot_log_in(anonymous, demo, monkeypatch):
    monkeypatch.setattr(config, "DEMO_ACCOUNTS", False)
    assert password_login(anonymous).status_code == 401
    # And they are not created on start either
    from database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_demo_accounts(db)
        from models.user import User

        assert db.query(User).count() == 0


def test_code_login_of_normal_users_still_works(anonymous):
    from tests.conftest import last_code

    assert anonymous.post("/auth/register", json={"name": "Luis", "email": "luis@pyme.com"}).status_code == 201
    r = anonymous.post("/auth/verify", json={"email": "luis@pyme.com", "code": last_code("luis@pyme.com")})
    assert r.status_code == 200
