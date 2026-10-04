from tests.conftest import TARIFAS


def test_crear_cotizacion_en_borrador(client, cotizacion):
    assert cotizacion["estado"] == "borrador" and cotizacion["total"] == 0 and cotizacion["items"] == []


def test_cliente_inexistente_da_404(client):
    r = client.post("/cotizaciones", json={"cliente_id": 99, "titulo": "Proyecto X", "descripcion_alcance": "Una tienda en línea con pagos"})
    assert r.status_code == 404


def test_analizar_genera_items_estimacion_y_total(cotizacion_analizada):
    c = cotizacion_analizada
    assert c["items"] and c["total"] > 0
    assert c["estimacion"]["horas_esperadas"] > 0
    assert c["financiero"]["total"] == c["total"]
    assert {i["origen"] for i in c["items"]} == {"ia"}


def test_analizar_sin_tarifas_da_409_y_no_guarda_nada(client, cotizacion):
    r = client.post(f"/cotizaciones/{cotizacion['id']}/analizar")
    assert r.status_code == 409 and "rate" in r.json()["detail"].lower()
    assert client.get(f"/cotizaciones/{cotizacion['id']}").json()["items"] == []


def test_analizar_alcance_vago_da_422(client, tarifas, cliente_id):
    c = client.post("/cotizaciones", json={"cliente_id": cliente_id, "titulo": "Vago", "descripcion_alcance": "Quiero algo bonito para mi negocio"}).json()
    assert client.post(f"/cotizaciones/{c['id']}/analizar").status_code == 422


def test_reanalizar_no_duplica_items(client, cotizacion_analizada):
    n = len(cotizacion_analizada["items"])
    r = client.post(f"/cotizaciones/{cotizacion_analizada['id']}/analizar")
    assert len(r.json()["items"]) == n


def test_cambiar_margen_recalcula_el_total(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    antes = cotizacion_analizada["total"]
    r = client.put(f"/cotizaciones/{cid}", json={"margen_pct": 50})
    assert r.status_code == 200 and r.json()["total"] > antes
    r = client.put(f"/cotizaciones/{cid}", json={"descuento_pct": 10})
    assert r.json()["total"] < client.put(f"/cotizaciones/{cid}", json={"descuento_pct": 0}).json()["total"]


def test_cambiar_una_tarifa_se_refleja_al_recalcular(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    tarifa_backend = next(t for t in client.get("/tarifas").json() if t["rol"] == "Backend")
    client.put(f"/tarifas/{tarifa_backend['id']}", json={"rol": "Backend", "valor_hora": TARIFAS["Backend"] * 2})
    r = client.put(f"/cotizaciones/{cid}", json={"titulo": "Tienda en línea v2"})
    assert r.json()["total"] > cotizacion_analizada["total"]


def test_resumen(client, cotizacion_analizada):
    r = client.get(f"/cotizaciones/{cotizacion_analizada['id']}/resumen").json()
    assert r["cliente"] == "Ana Pérez" and r["total"] == cotizacion_analizada["total"]
    assert r["rango_horas"][0] < r["horas_esperadas"] < r["rango_horas"][1]
    assert r["tiene_propuesta"] is False


def test_listar_y_filtrar(client, cotizacion_analizada):
    assert len(client.get("/cotizaciones").json()) == 1
    assert client.get("/cotizaciones?estado=aceptada").json() == []
    assert len(client.get("/cotizaciones?estado=borrador").json()) == 1


def test_eliminar_borrador_elimina_sus_items(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    assert client.delete(f"/cotizaciones/{cid}").status_code == 200
    assert client.get(f"/cotizaciones/{cid}").status_code == 404


def test_cotizacion_inexistente(client):
    assert client.get("/cotizaciones/999").status_code == 404
    assert client.post("/cotizaciones/999/analizar").status_code == 404


def test_similares(client, tarifas, cliente_id, cotizacion):
    client.post("/cotizaciones", json={"cliente_id": cliente_id, "titulo": "Otra tienda", "descripcion_alcance": "Tienda en línea con catálogo de productos y pagos en línea"})
    client.post("/cotizaciones", json={"cliente_id": cliente_id, "titulo": "Intranet", "descripcion_alcance": "Intranet de documentos para recursos humanos"})
    r = client.get(f"/cotizaciones/{cotizacion['id']}/similares").json()
    assert r[0]["titulo"] == "Otra tienda"
    assert r[0]["similitud"] >= r[-1]["similitud"]


def test_cliente_con_cotizaciones_no_se_elimina(client, cliente_id, cotizacion):
    r = client.delete(f"/clientes/{cliente_id}")
    assert r.status_code == 409
