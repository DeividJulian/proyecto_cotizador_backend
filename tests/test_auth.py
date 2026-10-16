import jwt
import pytest

import config
import services.auth as auth
from database import SessionLocal
from models.tarifa import Tarifa
from models.usuario import Usuario
from services.auth import crear_token
from tests.conftest import TARIFAS, VERIFICADOR_REAL, credencial, entrar


def login(anonimo, valor):
    return anonimo.post("/auth/google", json={"credencial": valor})


# ---------- Entrar con Google ----------

def test_primer_login_crea_la_cuenta_con_tarifas_de_mercado(anonimo):
    r = login(anonimo, credencial("ana@pyme.com", "Ana Pérez"))
    assert r.status_code == 200
    datos = r.json()
    assert datos["token"] and datos["usuario"]["email"] == "ana@pyme.com" and datos["usuario"]["nombre"] == "Ana Pérez"
    assert datos["usuario"]["foto_url"]
    perfil = anonimo.get("/auth/me", headers={"Authorization": f"Bearer {datos['token']}"})
    assert perfil.status_code == 200 and perfil.json()["id"] == datos["usuario"]["id"]
    with SessionLocal() as db:
        assert {t.rol: t.valor_hora for t in db.query(Tarifa).all()} == TARIFAS


def test_volver_a_entrar_recupera_la_misma_cuenta_y_su_progreso(anonimo):
    primera = entrar("ana@pyme.com", "Ana Pérez")
    cot = primera.post("/cotizaciones", json={"titulo": "Mi tienda", "descripcion_alcance": "Una tienda en línea con pagos"}).json()

    r = login(anonimo, credencial("ana@pyme.com", "Ana P."))
    segunda = anonimo
    segunda.headers["Authorization"] = f"Bearer {r.json()['token']}"
    assert r.json()["usuario"]["nombre"] == "Ana P."  # se actualiza con los datos de Google
    assert [c["id"] for c in segunda.get("/cotizaciones").json()] == [cot["id"]]
    with SessionLocal() as db:
        assert db.query(Usuario).count() == 1
        assert db.query(Tarifa).count() == len(TARIFAS)  # no se duplican las tarifas


def test_la_cuenta_se_reconoce_por_el_id_de_google_aunque_cambie_el_correo(anonimo):
    login(anonimo, credencial("ana@pyme.com", sub="google-123"))
    r = login(anonimo, credencial("ana.nueva@pyme.com", sub="google-123"))
    assert r.json()["usuario"]["email"] == "ana.nueva@pyme.com"
    with SessionLocal() as db:
        assert db.query(Usuario).count() == 1


def test_correo_sin_distinguir_mayusculas(anonimo):
    r = login(anonimo, credencial("Ana@Pyme.COM"))
    assert r.json()["usuario"]["email"] == "ana@pyme.com"


def test_cuentas_distintas_no_se_mezclan(anonimo):
    a = login(anonimo, credencial("ana@pyme.com")).json()["usuario"]["id"]
    b = login(anonimo, credencial("luis@otra.com")).json()["usuario"]["id"]
    assert a != b


# ---------- Credenciales rechazadas ----------

def test_credencial_de_google_invalida_da_401(anonimo):
    r = login(anonimo, "x" * 40)
    assert r.status_code == 401 and "Google" in r.json()["detail"]
    with SessionLocal() as db:
        assert db.query(Usuario).count() == 0


def test_cuenta_de_google_sin_correo_verificado_da_401(anonimo):
    assert login(anonimo, credencial("ana@pyme.com", verificado=False)).status_code == 401


def test_credencial_vacia_o_muy_corta_da_422(anonimo):
    assert login(anonimo, "").status_code == 422
    assert anonimo.post("/auth/google", json={}).status_code == 422


def test_sin_google_client_id_en_el_servidor_da_503(anonimo, monkeypatch):
    monkeypatch.setattr(auth, "verificar_token_google", VERIFICADOR_REAL)
    monkeypatch.setattr(config, "GOOGLE_CLIENT_ID", "")
    r = login(anonimo, credencial("ana@pyme.com"))
    assert r.status_code == 503 and "not configured" in r.json()["detail"]


def test_si_google_no_responde_da_503(anonimo, monkeypatch):
    def google_caido(_valor):
        raise auth.GoogleNoDisponible("timeout")

    monkeypatch.setattr(auth, "verificar_token_google", google_caido)
    r = login(anonimo, credencial("ana@pyme.com"))
    assert r.status_code == 503 and "Google" in r.json()["detail"]


def test_verificador_real_valida_audiencia_y_emisor(monkeypatch):
    """Sin red: se reemplaza la verificación criptográfica de google-auth y se revisa lo que exige el verificador."""
    from google.oauth2 import id_token

    recibido = {}

    def verify_falso(token, request, audience):
        recibido["audiencia"] = audience
        return {"iss": "https://evil.example.com", "sub": "1", "email": "a@b.com", "email_verified": True}

    monkeypatch.setattr(id_token, "verify_oauth2_token", verify_falso)
    with pytest.raises(auth.TokenGoogleInvalido):
        VERIFICADOR_REAL("x" * 40)
    assert recibido["audiencia"] == config.GOOGLE_CLIENT_ID

    def firma_invalida(token, request, audience):
        raise ValueError("Could not verify token signature")

    monkeypatch.setattr(id_token, "verify_oauth2_token", firma_invalida)
    with pytest.raises(auth.TokenGoogleInvalido):
        VERIFICADOR_REAL("x" * 40)


# ---------- Tokens de sesión ----------

def test_me_sin_token_da_401(anonimo):
    assert anonimo.get("/auth/me").status_code == 401


@pytest.mark.parametrize(
    "token", ["basura", jwt.encode({"sub": "1"}, "otra-clave-distinta-de-al-menos-32-bytes", algorithm="HS256")]
)
def test_token_invalido_o_firmado_con_otra_clave_da_401(anonimo, token):
    entrar("ana@pyme.com")
    assert anonimo.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_vencido_da_401(anonimo):
    entrar("ana@pyme.com")
    with SessionLocal() as db:
        token = crear_token(db.query(Usuario).one(), horas=-1)
    assert anonimo.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_token_de_una_cuenta_que_ya_no_existe_da_401(anonimo):
    entrar("ana@pyme.com")
    with SessionLocal() as db:
        usuario = db.query(Usuario).one()
        token = crear_token(usuario)
        db.query(Tarifa).delete()
        db.delete(usuario)
        db.commit()
    assert anonimo.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
