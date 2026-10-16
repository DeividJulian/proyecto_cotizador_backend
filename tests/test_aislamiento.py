"""Cada usuario solo ve y modifica lo suyo: sus cotizaciones, ítems, propuestas, tarifas y estadísticas."""
import pytest

from tests.conftest import ALCANCE

RUTAS_PRIVADAS = [
    ("get", "/cotizaciones"),
    ("post", "/cotizaciones"),
    ("get", "/cotizaciones/1"),
    ("put", "/cotizaciones/1"),
    ("delete", "/cotizaciones/1"),
    ("post", "/cotizaciones/1/analizar"),
    ("get", "/cotizaciones/1/resumen"),
    ("post", "/cotizaciones/1/estado"),
    ("get", "/cotizaciones/1/similares"),
    ("get", "/cotizaciones/1/items"),
    ("post", "/cotizaciones/1/items"),
    ("get", "/cotizaciones/1/propuesta"),
    ("post", "/cotizaciones/1/propuesta"),
    ("get", "/tarifas"),
    ("post", "/tarifas"),
    ("post", "/tarifas/restablecer"),
    ("post", "/alcance/estimar"),
    ("post", "/finanzas/simular"),
    ("get", "/estadisticas"),
    ("post", "/seed"),
]


def llamar(sesion, metodo, ruta):
    return getattr(sesion, metodo)(ruta, **({"json": {}} if metodo in ("post", "put") else {}))


@pytest.mark.parametrize("metodo,ruta", RUTAS_PRIVADAS)
def test_sin_sesion_da_401(anonimo, metodo, ruta):
    assert llamar(anonimo, metodo, ruta).status_code == 401


def test_rutas_publicas_no_piden_sesion(anonimo):
    assert anonimo.get("/").status_code == 200
    assert anonimo.get("/health").status_code == 200
    assert anonimo.get("/tarifas/mercado").status_code == 200


def test_otro_usuario_no_ve_ni_toca_mis_cotizaciones(cotizacion_analizada, otro):
    cid = cotizacion_analizada["id"]
    assert otro.get("/cotizaciones").json() == []
    for metodo, ruta in [
        ("get", f"/cotizaciones/{cid}"),
        ("get", f"/cotizaciones/{cid}/resumen"),
        ("put", f"/cotizaciones/{cid}"),
        ("delete", f"/cotizaciones/{cid}"),
        ("post", f"/cotizaciones/{cid}/analizar"),
        ("get", f"/cotizaciones/{cid}/items"),
        ("post", f"/cotizaciones/{cid}/propuesta"),
        ("get", f"/cotizaciones/{cid}/propuesta"),
        ("get", f"/cotizaciones/{cid}/similares"),
    ]:
        assert llamar(otro, metodo, ruta).status_code == 404, ruta
    assert otro.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"}).status_code == 404


def test_otro_usuario_no_toca_mis_items(client, cotizacion_analizada, otro):
    cid = cotizacion_analizada["id"]
    item = cotizacion_analizada["items"][0]
    assert otro.delete(f"/cotizaciones/{cid}/items/{item['id']}").status_code == 404
    assert otro.put(f"/cotizaciones/{cid}/items/{item['id']}", json={"horas_probable": 1}).status_code == 404
    assert len(client.get(f"/cotizaciones/{cid}/items").json()) == len(cotizacion_analizada["items"])


def test_las_tarifas_son_de_cada_usuario(client, otro):
    mia = next(t for t in client.get("/tarifas").json() if t["rol"] == "Backend")
    assert otro.put(f"/tarifas/{mia['id']}", json={"rol": "Backend", "valor_hora": 1}).status_code == 404
    assert otro.delete(f"/tarifas/{mia['id']}").status_code == 404
    client.put(f"/tarifas/{mia['id']}", json={"rol": "Backend", "valor_hora": 120000})
    de_luis = next(t for t in otro.get("/tarifas").json() if t["rol"] == "Backend")
    assert de_luis["valor_hora"] != 120000
    # cada uno puede tener su propio "Data Science"
    assert client.post("/tarifas", json={"rol": "Data Science", "valor_hora": 90000}).status_code == 201
    assert otro.post("/tarifas", json={"rol": "Data Science", "valor_hora": 70000}).status_code == 201


def test_el_precio_usa_las_tarifas_del_dueno(client, otro):
    cuerpo = {"titulo": "Tienda", "descripcion_alcance": ALCANCE}
    mia = client.post("/cotizaciones", json=cuerpo).json()
    de_luis = otro.post("/cotizaciones", json=cuerpo).json()
    for t in otro.get("/tarifas").json():  # Luis cobra el doble
        otro.put(f"/tarifas/{t['id']}", json={"rol": t["rol"], "valor_hora": t["valor_hora"] * 2})
    total_mio = client.post(f"/cotizaciones/{mia['id']}/analizar").json()["total"]
    total_luis = otro.post(f"/cotizaciones/{de_luis['id']}/analizar").json()["total"]
    assert total_luis == pytest.approx(total_mio * 2, rel=0.001)


def test_similares_solo_compara_con_mis_cotizaciones(client, cotizacion, otro):
    otro.post("/cotizaciones", json={"titulo": "Tienda de Luis", "descripcion_alcance": ALCANCE})
    assert client.get(f"/cotizaciones/{cotizacion['id']}/similares").json() == []


def test_el_usuario_maneja_todo_el_ciclo_de_su_cotizacion(client, cotizacion_analizada):
    """Sin administrador: el mismo usuario genera la propuesta, la envía a su cliente y registra la respuesta."""
    cid = cotizacion_analizada["id"]
    assert client.post(f"/cotizaciones/{cid}/propuesta").status_code == 200
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"}).status_code == 200
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "aceptada"}).json()["estado"] == "aceptada"
