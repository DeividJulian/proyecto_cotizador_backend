from services.alcance import analizar_alcance
from services.catalogo import MODULOS
from services.estimacion import construir_items, pert, resumen_estimacion
from tests.conftest import ALCANCE


def claves(texto):
    return {m["clave"] for m in analizar_alcance(texto)["modulos"]}


def test_distribuciones_del_catalogo_suman_uno():
    for clave, m in MODULOS.items():
        assert abs(sum(m["distribucion"].values()) - 1) < 1e-9, clave


def test_detecta_modulos_del_alcance():
    assert {"autenticacion", "catalogo", "pagos", "panel_admin", "reportes"} <= claves(ALCANCE)


def test_ignora_acentos_y_mayusculas():
    assert "autenticacion" in claves("NECESITAMOS INICIO DE SESIÓN y permisos para el equipo")


def test_alcance_vago_no_detecta_modulos_y_advierte():
    r = analizar_alcance("Quiero algo bonito para mi negocio de verdad")
    assert r["modulos"] == [] and r["advertencias"]


def test_senal_de_complejidad_alta():
    r = analizar_alcance("Un sistema de reportes complejo con tablero de indicadores")
    modulo = next(m for m in r["modulos"] if m["clave"] == "reportes")
    assert modulo["complejidad"] == "alta"


def test_senal_de_complejidad_baja():
    r = analizar_alcance("Un sitio web institucional sencillo para la empresa")
    modulo = next(m for m in r["modulos"] if m["clave"] == "sitio_web")
    assert modulo["complejidad"] == "baja"


def test_pert_formula():
    assert pert(6, 12, 24) == (6 + 48 + 24) / 6


def test_alta_complejidad_cuesta_mas_que_baja():
    base = [{"clave": "pagos", "nombre": "Pagos", "categoria": "Negocio", "motivos": ""}]
    baja = construir_items([{**base[0], "complejidad": "baja"}])[0]
    alta = construir_items([{**base[0], "complejidad": "alta"}])[0]
    assert alta["horas_esperadas"] > baja["horas_esperadas"]
    assert baja["horas_optimista"] < baja["horas_probable"] < baja["horas_pesimista"]


def test_transversales_se_agregan_con_minimo():
    items = construir_items([{"clave": "sitio_web", "nombre": "Sitio", "categoria": "Contenido",
                              "complejidad": "baja", "motivos": ""}])
    transversales = [i for i in items if i["categoria"] == "Cross-cutting"]
    assert len(transversales) == 3
    assert all(i["horas_probable"] >= 8 for i in transversales)


def test_resumen_suma_las_horas_por_rol():
    items = construir_items(analizar_alcance(ALCANCE)["modulos"])
    r = resumen_estimacion(items)
    suma_roles = round(sum(f["esperadas"] for f in r["por_rol"].values()), 1)
    assert abs(r["horas_esperadas"] - suma_roles) < 0.2
    assert r["horas_optimista"] < r["horas_esperadas"] < r["horas_pesimista"]


def test_endpoint_analizar_y_estimar(client):
    r = client.post("/alcance/analizar", json={"descripcion_alcance": ALCANCE})
    assert r.status_code == 200 and r.json()["modulos"]
    r = client.post("/alcance/estimar", json={"descripcion_alcance": ALCANCE})
    assert r.status_code == 200 and r.json()["estimacion"]["horas_esperadas"] > 0


def test_estimar_alcance_vago_da_422(client):
    r = client.post("/alcance/estimar", json={"descripcion_alcance": "Quiero algo bonito para mi negocio"})
    assert r.status_code == 422
