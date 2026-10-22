import json
from datetime import timedelta

import jwt
import pytest

import config
from database import SessionLocal
from models.rate import Rate
from models.user import User, VerificationCode
from services import mailer
from services.auth import create_token, now
from services.mailer import OUTBOX
from tests.conftest import RATES, last_code, log_in


def register(anonymous, email="ana@pyme.com", name="Ana Pérez"):
    return anonymous.post("/auth/register", json={"name": name, "email": email})


def verify(anonymous, email, code):
    return anonymous.post("/auth/verify", json={"email": email, "code": code})


def no_wait(monkeypatch):
    monkeypatch.setattr(config, "CODE_WAIT_SECONDS", 0)


def wrong(code: str) -> str:
    return "000000" if code != "000000" else "111111"


# ---------- Sign up and verification ----------

def test_sign_up_emails_a_code_and_leaves_the_account_unverified(anonymous):
    r = register(anonymous)
    assert r.status_code == 201 and r.json()["message"] == "Te enviamos un código de verificación al correo"
    assert len(OUTBOX) == 1 and OUTBOX[0]["to"] == "ana@pyme.com"
    assert "código de verificación" in OUTBOX[0]["subject"] and "Hola Ana Pérez" in OUTBOX[0]["text"]
    assert len(last_code("ana@pyme.com")) == 6
    with SessionLocal() as db:
        assert db.query(User).one().verified is False
        assert db.query(Rate).count() == 0  # rates are loaded on verification
        # the code is never stored as plain text
        assert last_code("ana@pyme.com") not in db.query(VerificationCode).one().code_hash


def test_verifying_activates_the_account_with_market_rates(anonymous):
    register(anonymous)
    r = verify(anonymous, "ana@pyme.com", last_code("ana@pyme.com"))
    assert r.status_code == 200
    data = r.json()
    assert data["token"] and data["user"]["email"] == "ana@pyme.com"
    me = anonymous.get("/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert me.status_code == 200 and me.json()["name"] == "Ana Pérez"
    with SessionLocal() as db:
        assert {r.role: r.hourly_rate for r in db.query(Rate).all()} == RATES


def test_logging_in_again_recovers_the_account_and_its_progress(anonymous, monkeypatch):
    no_wait(monkeypatch)
    first = log_in("ana@pyme.com")
    quote = first.post("/quotes", json={"title": "Mi tienda", "scope_description": "Una tienda en línea con pagos"}).json()

    anonymous.post("/auth/login", json={"email": "ana@pyme.com"})
    r = verify(anonymous, "ana@pyme.com", last_code("ana@pyme.com"))
    anonymous.headers["Authorization"] = f"Bearer {r.json()['token']}"
    assert [q["id"] for q in anonymous.get("/quotes").json()] == [quote["id"]]
    with SessionLocal() as db:
        assert db.query(Rate).count() == len(RATES)  # rates are not duplicated


def test_email_is_case_insensitive(anonymous, monkeypatch):
    no_wait(monkeypatch)
    register(anonymous, email="Ana@Pyme.COM")
    assert verify(anonymous, "ana@pyme.com", last_code("ana@pyme.com")).status_code == 200
    assert anonymous.post("/auth/login", json={"email": "ANA@pyme.com"}).status_code == 200


def test_signing_up_twice_with_a_verified_account_returns_409(anonymous):
    log_in("ana@pyme.com")
    r = register(anonymous)
    assert r.status_code == 409 and r.json()["detail"] == "Ya existe una cuenta con ese correo: inicia sesión"


def test_signing_up_again_without_verifying_resends_the_code(anonymous, monkeypatch):
    no_wait(monkeypatch)
    register(anonymous)
    first = last_code("ana@pyme.com")
    assert register(anonymous, name="Ana María").status_code == 201
    assert len(OUTBOX) == 2
    with SessionLocal() as db:
        assert db.query(User).count() == 1 and db.query(User).one().name == "Ana María"
    second = last_code("ana@pyme.com")
    if first != second:  # the previous code is invalidated
        assert verify(anonymous, "ana@pyme.com", first).status_code == 400
    assert verify(anonymous, "ana@pyme.com", second).status_code == 200


def test_invalid_sign_up_data(anonymous):
    assert anonymous.post("/auth/register", json={"name": "A", "email": "ana@pyme.com"}).status_code == 422
    assert anonymous.post("/auth/register", json={"name": "Ana", "email": "no-es-correo"}).status_code == 422
    assert OUTBOX == []


# ---------- Log in with a code ----------

def test_logging_in_with_an_unknown_email_returns_404(anonymous):
    r = anonymous.post("/auth/login", json={"email": "nadie@x.com"})
    assert r.status_code == 404 and "regístrate" in r.json()["detail"]
    assert OUTBOX == []


def test_asking_for_another_code_too_soon_returns_429(anonymous):
    register(anonymous)
    r = anonymous.post("/auth/login", json={"email": "ana@pyme.com"})
    assert r.status_code == 429 and "segundos" in r.json()["detail"]
    assert len(OUTBOX) == 1


def test_the_login_email_says_it_is_for_logging_in(anonymous):
    log_in("ana@pyme.com")
    with SessionLocal() as db:  # pretends the last code was asked for a while ago
        db.query(VerificationCode).update({VerificationCode.created_at: now() - timedelta(minutes=5)})
        db.commit()
    assert anonymous.post("/auth/login", json={"email": "ana@pyme.com"}).status_code == 200
    assert "entrar" in OUTBOX[-1]["subject"] and "iniciar sesión" in OUTBOX[-1]["text"]


# ---------- Code security ----------

def test_a_wrong_code_counts_an_attempt(anonymous):
    register(anonymous)
    code = last_code("ana@pyme.com")
    r = verify(anonymous, "ana@pyme.com", wrong(code))
    assert r.status_code == 400 and f"Te quedan {config.CODE_ATTEMPTS - 1} intentos" in r.json()["detail"]
    assert verify(anonymous, "ana@pyme.com", code).status_code == 200


def test_after_all_attempts_the_right_code_no_longer_works(anonymous):
    register(anonymous)
    code = last_code("ana@pyme.com")
    for _ in range(config.CODE_ATTEMPTS):
        assert verify(anonymous, "ana@pyme.com", wrong(code)).status_code == 400
    r = verify(anonymous, "ana@pyme.com", code)
    assert r.status_code == 400 and "No hay un código activo" in r.json()["detail"]


def test_an_expired_code_does_not_work(anonymous):
    register(anonymous)
    with SessionLocal() as db:
        db.query(VerificationCode).update({VerificationCode.expires_at: now() - timedelta(seconds=1)})
        db.commit()
    r = verify(anonymous, "ana@pyme.com", last_code("ana@pyme.com"))
    assert r.status_code == 400 and "venció" in r.json()["detail"]


def test_the_code_works_only_once(anonymous):
    register(anonymous)
    code = last_code("ana@pyme.com")
    assert verify(anonymous, "ana@pyme.com", code).status_code == 200
    assert verify(anonymous, "ana@pyme.com", code).status_code == 400


def test_a_new_code_invalidates_the_previous_one(anonymous, monkeypatch):
    no_wait(monkeypatch)
    register(anonymous)
    old = last_code("ana@pyme.com")
    anonymous.post("/auth/login", json={"email": "ana@pyme.com"})
    new = last_code("ana@pyme.com")
    if old != new:
        assert verify(anonymous, "ana@pyme.com", old).status_code == 400
    assert verify(anonymous, "ana@pyme.com", new).status_code == 200


def test_a_code_with_a_wrong_format_returns_422(anonymous):
    register(anonymous)
    assert verify(anonymous, "ana@pyme.com", "12ab56").status_code == 422
    assert verify(anonymous, "ana@pyme.com", "123").status_code == 422


def test_verifying_an_unknown_email_returns_400(anonymous):
    assert verify(anonymous, "nadie@x.com", "123456").status_code == 400


# ---------- Tokens ----------

def test_me_without_a_token_returns_401(anonymous):
    r = anonymous.get("/auth/me")
    assert r.status_code == 401 and r.json()["detail"] == "Debes iniciar sesión"


@pytest.mark.parametrize(
    "token", ["basura", jwt.encode({"sub": "1"}, "otra-clave-distinta-de-al-menos-32-bytes", algorithm="HS256")]
)
def test_invalid_or_foreign_token_returns_401(anonymous, token):
    log_in("ana@pyme.com")
    assert anonymous.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_expired_token_returns_401(anonymous):
    log_in("ana@pyme.com")
    with SessionLocal() as db:
        token = create_token(db.query(User).one(), hours=-1)
    r = anonymous.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401 and "venció" in r.json()["detail"]


def test_token_of_an_unverified_account_returns_401(anonymous):
    register(anonymous)
    with SessionLocal() as db:
        token = create_token(db.query(User).one())
    assert anonymous.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


# ---------- Email delivery ----------

def test_if_the_email_fails_it_returns_502_and_saves_no_account(anonymous, monkeypatch):
    def fail(*_args, **_kwargs):
        raise mailer.EmailError("provider down")

    monkeypatch.setattr("services.auth.send_email", fail)
    r = register(anonymous)
    assert r.status_code == 502 and "No pudimos enviar el correo" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.query(User).count() == 0


def test_brevo_backend_sends_the_right_request(monkeypatch):
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(request, timeout):
        sent.append(request)
        return Response()

    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "clave-brevo")
    monkeypatch.setattr(config, "EMAIL_FROM", "cotizador@ejemplo.com")
    monkeypatch.setattr(mailer.urllib.request, "urlopen", fake_urlopen)
    mailer.send_email("ana@pyme.com", "Asunto", "Tu código es 123456")

    request = sent[0]
    assert request.full_url == mailer.BREVO_URL and request.get_header("Api-key") == "clave-brevo"
    body = json.loads(request.data)
    assert body["to"] == [{"email": "ana@pyme.com"}] and body["sender"]["email"] == "cotizador@ejemplo.com"
    assert "123456" in body["textContent"]


def test_brevo_backend_without_api_key_raises_an_email_error(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    with pytest.raises(mailer.EmailError):
        mailer.send_email("ana@pyme.com", "Asunto", "Texto")


def test_spanish_names_of_the_email_backend_still_work(monkeypatch):
    import importlib

    monkeypatch.setenv("EMAIL_BACKEND", "consola")
    try:
        assert importlib.reload(config).EMAIL_BACKEND == "console"
    finally:
        monkeypatch.setenv("EMAIL_BACKEND", "memory")
        importlib.reload(config)
