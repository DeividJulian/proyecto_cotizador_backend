import json
from datetime import timedelta

import jwt
import pytest

import config
from database import SessionLocal
from models.tarifa import Tarifa
from models.usuario import CodigoVerificacion, Usuario
from services import correo
from services.auth import ahora, crear_token
from services.correo import BANDEJA
from tests.conftest import TARIFAS, entrar, ultimo_codigo


def registrar(anonimo, email="ana@pyme.com", nombre="Ana Pérez"):
    return anonimo.post("/auth/registro", json={"nombre": nombre, "email": email})


def verificar(anonimo, email, codigo):
    return anonimo.post("/auth/verificar", json={"email": email, "codigo": codigo})


def sin_espera(monkeypatch):
    monkeypatch.setattr(config, "CODIGO_ESPERA_SEGUNDOS", 0)


def incorrecto(codigo: str) -> str:
    return "000000" if codigo != "000000" else "111111"


# ---------- Registro y verificación ----------

def test_registro_envia_correo_con_codigo_y_la_cuenta_queda_sin_verificar(anonimo):
    r = registrar(anonimo)
    assert r.status_code == 201
    assert len(BANDEJA) == 1 and BANDEJA[0]["para"] == "ana@pyme.com"
    assert len(ultimo_codigo("ana@pyme.com")) == 6
    with SessionLocal() as db:
        assert db.query(Usuario).one().verificado is False
        assert db.query(Tarifa).count() == 0  # las tarifas se cargan al verificar
        # el código nunca se guarda en texto plano
        assert ultimo_codigo("ana@pyme.com") not in db.query(CodigoVerificacion).one().codigo_hash


def test_verificar_activa_la_cuenta_con_tarifas_de_mercado(anonimo):
    registrar(anonimo)
    r = verificar(anonimo, "ana@pyme.com", ultimo_codigo("ana@pyme.com"))
    assert r.status_code == 200
    datos = r.json()
    assert datos["token"] and datos["usuario"]["email"] == "ana@pyme.com"
    perfil = anonimo.get("/auth/me", headers={"Authorization": f"Bearer {datos['token']}"})
    assert perfil.status_code == 200 and perfil.json()["nombre"] == "Ana Pérez"
    with SessionLocal() as db:
        assert {t.rol: t.valor_hora for t in db.query(Tarifa).all()} == TARIFAS


def test_volver_a_entrar_recupera_la_cuenta_y_su_progreso(anonimo, monkeypatch):
    sin_espera(monkeypatch)
    primera = entrar("ana@pyme.com")
    cot = primera.post("/cotizaciones", json={"titulo": "Mi tienda", "descripcion_alcance": "Una tienda en línea con pagos"}).json()

    anonimo.post("/auth/login", json={"email": "ana@pyme.com"})
    r = verificar(anonimo, "ana@pyme.com", ultimo_codigo("ana@pyme.com"))
    anonimo.headers["Authorization"] = f"Bearer {r.json()['token']}"
    assert [c["id"] for c in anonimo.get("/cotizaciones").json()] == [cot["id"]]
    with SessionLocal() as db:
        assert db.query(Tarifa).count() == len(TARIFAS)  # no se duplican las tarifas


def test_email_sin_distinguir_mayusculas(anonimo, monkeypatch):
    sin_espera(monkeypatch)
    registrar(anonimo, email="Ana@Pyme.COM")
    assert verificar(anonimo, "ana@pyme.com", ultimo_codigo("ana@pyme.com")).status_code == 200
    assert anonimo.post("/auth/login", json={"email": "ANA@pyme.com"}).status_code == 200


def test_registro_duplicado_de_cuenta_verificada_da_409(anonimo):
    entrar("ana@pyme.com")
    assert registrar(anonimo).status_code == 409


def test_registro_repetido_sin_verificar_reenvia_el_codigo(anonimo, monkeypatch):
    sin_espera(monkeypatch)
    registrar(anonimo)
    primero = ultimo_codigo("ana@pyme.com")
    assert registrar(anonimo, nombre="Ana María").status_code == 201
    assert len(BANDEJA) == 2
    with SessionLocal() as db:
        assert db.query(Usuario).count() == 1 and db.query(Usuario).one().nombre == "Ana María"
    segundo = ultimo_codigo("ana@pyme.com")
    if primero != segundo:  # el código anterior queda invalidado
        assert verificar(anonimo, "ana@pyme.com", primero).status_code == 400
    assert verificar(anonimo, "ana@pyme.com", segundo).status_code == 200


def test_datos_de_registro_invalidos(anonimo):
    assert anonimo.post("/auth/registro", json={"nombre": "A", "email": "ana@pyme.com"}).status_code == 422
    assert anonimo.post("/auth/registro", json={"nombre": "Ana", "email": "no-es-correo"}).status_code == 422
    assert BANDEJA == []


# ---------- Login con código ----------

def test_login_de_email_no_registrado_da_404(anonimo):
    assert anonimo.post("/auth/login", json={"email": "nadie@x.com"}).status_code == 404
    assert BANDEJA == []


def test_pedir_otro_codigo_demasiado_pronto_da_429(anonimo):
    registrar(anonimo)
    r = anonimo.post("/auth/login", json={"email": "ana@pyme.com"})
    assert r.status_code == 429 and "seconds" in r.json()["detail"]
    assert len(BANDEJA) == 1


def test_el_correo_de_login_dice_que_es_para_entrar(anonimo):
    entrar("ana@pyme.com")
    with SessionLocal() as db:  # simula que el último código se pidió hace rato
        db.query(CodigoVerificacion).update({"creado_en": ahora() - timedelta(minutes=5)})
        db.commit()
    assert anonimo.post("/auth/login", json={"email": "ana@pyme.com"}).status_code == 200
    assert "login" in BANDEJA[-1]["asunto"].lower()


# ---------- Seguridad del código ----------

def test_codigo_incorrecto_descuenta_intentos(anonimo):
    registrar(anonimo)
    codigo = ultimo_codigo("ana@pyme.com")
    r = verificar(anonimo, "ana@pyme.com", incorrecto(codigo))
    assert r.status_code == 400 and f"Attempts left: {config.CODIGO_INTENTOS - 1}" in r.json()["detail"]
    assert verificar(anonimo, "ana@pyme.com", codigo).status_code == 200


def test_tras_agotar_los_intentos_el_codigo_correcto_ya_no_sirve(anonimo):
    registrar(anonimo)
    codigo = ultimo_codigo("ana@pyme.com")
    for _ in range(config.CODIGO_INTENTOS):
        assert verificar(anonimo, "ana@pyme.com", incorrecto(codigo)).status_code == 400
    r = verificar(anonimo, "ana@pyme.com", codigo)
    assert r.status_code == 400 and "no active code" in r.json()["detail"]


def test_codigo_vencido_no_sirve(anonimo):
    registrar(anonimo)
    with SessionLocal() as db:
        db.query(CodigoVerificacion).update({"expira_en": ahora() - timedelta(seconds=1)})
        db.commit()
    r = verificar(anonimo, "ana@pyme.com", ultimo_codigo("ana@pyme.com"))
    assert r.status_code == 400 and "expired" in r.json()["detail"]


def test_el_codigo_es_de_un_solo_uso(anonimo):
    registrar(anonimo)
    codigo = ultimo_codigo("ana@pyme.com")
    assert verificar(anonimo, "ana@pyme.com", codigo).status_code == 200
    assert verificar(anonimo, "ana@pyme.com", codigo).status_code == 400


def test_un_codigo_nuevo_invalida_el_anterior(anonimo, monkeypatch):
    sin_espera(monkeypatch)
    registrar(anonimo)
    viejo = ultimo_codigo("ana@pyme.com")
    anonimo.post("/auth/login", json={"email": "ana@pyme.com"})
    nuevo = ultimo_codigo("ana@pyme.com")
    if viejo != nuevo:
        assert verificar(anonimo, "ana@pyme.com", viejo).status_code == 400
    assert verificar(anonimo, "ana@pyme.com", nuevo).status_code == 200


def test_codigo_con_formato_invalido_da_422(anonimo):
    registrar(anonimo)
    assert verificar(anonimo, "ana@pyme.com", "12ab56").status_code == 422
    assert verificar(anonimo, "ana@pyme.com", "123").status_code == 422


def test_verificar_email_desconocido_da_400(anonimo):
    assert verificar(anonimo, "nadie@x.com", "123456").status_code == 400


# ---------- Tokens ----------

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


def test_token_de_cuenta_sin_verificar_da_401(anonimo):
    registrar(anonimo)
    with SessionLocal() as db:
        token = crear_token(db.query(Usuario).one())
    assert anonimo.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


# ---------- Envío de correos ----------

def test_si_el_correo_falla_responde_502_y_no_guarda_la_cuenta(anonimo, monkeypatch):
    def falla(*_args, **_kwargs):
        raise correo.ErrorCorreo("proveedor caído")

    monkeypatch.setattr("services.auth.enviar_correo", falla)
    assert registrar(anonimo).status_code == 502
    with SessionLocal() as db:
        assert db.query(Usuario).count() == 0


def test_backend_brevo_envia_la_peticion_correcta(monkeypatch):
    enviadas = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def urlopen_falso(peticion, timeout):
        enviadas.append(peticion)
        return Respuesta()

    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "clave-brevo")
    monkeypatch.setattr(config, "EMAIL_FROM", "cotizador@ejemplo.com")
    monkeypatch.setattr(correo.urllib.request, "urlopen", urlopen_falso)
    correo.enviar_correo("ana@pyme.com", "Asunto", "Tu código es 123456")

    peticion = enviadas[0]
    assert peticion.full_url == correo.BREVO_URL and peticion.get_header("Api-key") == "clave-brevo"
    cuerpo = json.loads(peticion.data)
    assert cuerpo["to"] == [{"email": "ana@pyme.com"}] and cuerpo["sender"]["email"] == "cotizador@ejemplo.com"
    assert "123456" in cuerpo["textContent"]


def test_backend_brevo_sin_api_key_falla_con_error_de_correo(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_BACKEND", "brevo")
    monkeypatch.setattr(config, "BREVO_API_KEY", "")
    with pytest.raises(correo.ErrorCorreo):
        correo.enviar_correo("ana@pyme.com", "Asunto", "Texto")
