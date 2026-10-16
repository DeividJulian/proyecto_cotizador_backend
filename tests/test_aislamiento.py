import pytest

from tests.conftest import ALCANCE, entrar

RUTAS_ADMIN = [
    ("get", "/clientes"),
    ("post", "/clientes"),
    ("get", "/tarifas"),
    ("post", "/tarifas"),
    ("post", "/alcance/estimar"),
    ("post", "/finanzas/simular"),
    ("get", "/estadisticas"),
    ("post", "/seed"),
    ("get", "/usuarios"),
    ("post", "/cotizaciones"),
    ("get", "/cotizaciones/1"),
    ("put", "/cotizaciones/1"),
    ("delete", "/cotizaciones/1"),
    ("post", "/cotizaciones/1/analizar"),
    ("post", "/cotizaciones/1/estado"),
    ("get", "/cotizaciones/1/similares"),
    ("get", "/cotizaciones/1/items"),
    ("post", "/cotizaciones/1/items"),
    ("post", "/cotizaciones/1/propuesta"),
]


def llamar(sesion, metodo, ruta):
    return getattr(sesion, metodo)(ruta, **({"json": {}} if metodo in ("post", "put") else {}))


@pytest.fixture
def cliente_ana():
    return entrar("ana@pyme.com", "Ana Pérez", "Pyme SAS")


@pytest.fixture
def cliente_luis():
    return entrar("luis@otra.com", "Luis Gómez")


def cotizacion_enviada(admin, cliente_id, titulo="Tienda en línea"):
    """Crea, analiza, genera propuesta y envía una cotización para ese cliente."""
    cot = admin.post("/cotizaciones", json={"cliente_id": cliente_id, "titulo": titulo, "descripcion_alcance": ALCANCE}).json()
    assert admin.post(f"/cotizaciones/{cot['id']}/analizar").status_code == 200
    assert admin.post(f"/cotizaciones/{cot['id']}/propuesta").status_code == 200
    assert admin.post(f"/cotizaciones/{cot['id']}/estado", json={"estado": "enviada"}).status_code == 200
    return cot["id"]


# ---------- Acceso sin sesión ----------

@pytest.mark.parametrize("metodo,ruta", RUTAS_ADMIN + [("get", "/cotizaciones"), ("get", "/cotizaciones/1/resumen")])
def test_sin_sesion_da_401(anonimo, metodo, ruta):
    assert llamar(anonimo, metodo, ruta).status_code == 401


def test_rutas_publicas_no_piden_sesion(anonimo):
    assert anonimo.get("/").status_code == 200
    assert anonimo.get("/health").status_code == 200


# ---------- Rol cliente ----------

@pytest.mark.parametrize("metodo,ruta", RUTAS_ADMIN)
def test_cliente_no_entra_a_rutas_de_admin(cliente_ana, metodo, ruta):
    r = llamar(cliente_ana, metodo, ruta)
    assert r.status_code == 403 and "administrators" in r.json()["detail"]


def test_cliente_solo_ve_sus_cotizaciones_enviadas(client, tarifas, cliente_ana, cliente_luis):
    ana_id = cliente_ana.get("/auth/me").json()["cliente_id"]
    luis_id = cliente_luis.get("/auth/me").json()["cliente_id"]
    enviada = cotizacion_enviada(client, ana_id)
    client.post("/cotizaciones", json={"cliente_id": ana_id, "titulo": "Borrador de Ana", "descripcion_alcance": ALCANCE})
    cotizacion_enviada(client, luis_id, "Proyecto de Luis")

    lista = cliente_ana.get("/cotizaciones").json()
    assert [c["id"] for c in lista] == [enviada]
    assert len(client.get("/cotizaciones").json()) == 3  # el admin ve todas


def test_cliente_ve_resumen_y_propuesta_de_su_cotizacion(client, tarifas, cliente_ana):
    cid = cotizacion_enviada(client, cliente_ana.get("/auth/me").json()["cliente_id"])
    r = cliente_ana.get(f"/cotizaciones/{cid}/resumen")
    assert r.status_code == 200 and r.json()["total"] > 0 and r.json()["tiene_propuesta"] is True
    assert "Commercial proposal" in cliente_ana.get(f"/cotizaciones/{cid}/propuesta").json()["propuesta"]
    assert cliente_ana.get(f"/cotizaciones/{cid}/propuesta/descargar").status_code == 200


def test_cliente_no_ve_cotizaciones_ajenas_ni_borradores(client, tarifas, cliente_ana, cliente_luis):
    luis = cotizacion_enviada(client, cliente_luis.get("/auth/me").json()["cliente_id"])
    borrador = client.post(
        "/cotizaciones",
        json={"cliente_id": cliente_ana.get("/auth/me").json()["cliente_id"], "titulo": "Borrador", "descripcion_alcance": ALCANCE},
    ).json()["id"]
    for cid in (luis, borrador):
        assert cliente_ana.get(f"/cotizaciones/{cid}/resumen").status_code == 404
        assert cliente_ana.get(f"/cotizaciones/{cid}/propuesta").status_code == 404
        assert cliente_ana.post(f"/cotizaciones/{cid}/respuesta", json={"estado": "aceptada"}).status_code == 404


def test_cliente_acepta_su_cotizacion_y_ya_no_puede_cambiarla(client, tarifas, cliente_ana):
    cid = cotizacion_enviada(client, cliente_ana.get("/auth/me").json()["cliente_id"])
    r = cliente_ana.post(f"/cotizaciones/{cid}/respuesta", json={"estado": "aceptada"})
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"
    assert client.get(f"/cotizaciones/{cid}").json()["estado"] == "aceptada"
    assert cliente_ana.post(f"/cotizaciones/{cid}/respuesta", json={"estado": "rechazada"}).status_code == 409


def test_cliente_rechaza_su_cotizacion(client, tarifas, cliente_ana):
    cid = cotizacion_enviada(client, cliente_ana.get("/auth/me").json()["cliente_id"])
    assert cliente_ana.post(f"/cotizaciones/{cid}/respuesta", json={"estado": "rechazada"}).json()["estado"] == "rechazada"


def test_cliente_no_puede_devolver_a_borrador(client, tarifas, cliente_ana):
    cid = cotizacion_enviada(client, cliente_ana.get("/auth/me").json()["cliente_id"])
    assert cliente_ana.post(f"/cotizaciones/{cid}/respuesta", json={"estado": "borrador"}).status_code == 422


# ---------- Gestión de usuarios (admin) ----------

def test_admin_lista_usuarios_y_cambia_roles(client, cliente_ana):
    usuarios = client.get("/usuarios").json()
    ana = next(u for u in usuarios if u["email"] == "ana@pyme.com")
    r = client.put(f"/usuarios/{ana['id']}/rol", json={"rol": "admin"})
    assert r.status_code == 200 and r.json()["rol"] == "admin"
    # el cambio aplica de inmediato, sin volver a iniciar sesión
    assert cliente_ana.get("/tarifas").status_code == 200
    client.put(f"/usuarios/{ana['id']}/rol", json={"rol": "cliente"})
    assert cliente_ana.get("/tarifas").status_code == 403


def test_admin_no_puede_cambiar_su_propio_rol(client):
    yo = client.get("/auth/me").json()
    assert client.put(f"/usuarios/{yo['id']}/rol", json={"rol": "cliente"}).status_code == 409


def test_rol_invalido_y_usuario_inexistente(client):
    assert client.put("/usuarios/999/rol", json={"rol": "cliente"}).status_code == 404
    assert client.put("/usuarios/1/rol", json={"rol": "superusuario"}).status_code == 422


# ---------- Integridad entre usuarios y clientes ----------

def test_no_se_elimina_un_cliente_con_cuenta_de_usuario(client, cliente_ana):
    ana_id = cliente_ana.get("/auth/me").json()["cliente_id"]
    r = client.delete(f"/clientes/{ana_id}")
    assert r.status_code == 409 and "user account" in r.json()["detail"]


def test_reiniciar_demo_conserva_las_cuentas_y_las_vuelve_a_ligar(client, anonimo, cliente_ana, monkeypatch):
    import config
    from tests.conftest import ultimo_codigo

    monkeypatch.setattr(config, "CODIGO_ESPERA_SEGUNDOS", 0)
    assert client.post("/seed").status_code == 409  # la ficha de Ana ya cuenta como datos existentes
    assert client.post("/seed?reiniciar=true").status_code == 200
    assert cliente_ana.get("/auth/me").json()["cliente_id"] is None  # su ficha se borró con el reinicio
    anonimo.post("/auth/login", json={"email": "ana@pyme.com"})
    r = anonimo.post("/auth/verificar", json={"email": "ana@pyme.com", "codigo": ultimo_codigo("ana@pyme.com")})
    assert r.json()["usuario"]["cliente_id"] is not None
