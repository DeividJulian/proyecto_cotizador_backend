def test_agregar_item_manual_recalcula(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    r = client.post(f"/cotizaciones/{cid}/items", json={"nombre": "Integración con ERP", "complejidad": "alta", "horas_probable": 40})
    assert r.status_code == 201
    c = r.json()
    assert c["total"] > cotizacion_analizada["total"]
    nuevo = next(i for i in c["items"] if i["nombre"] == "Integración con ERP")
    assert nuevo["origen"] == "manual" and nuevo["horas_optimista"] < 40 < nuevo["horas_pesimista"]


def test_distribucion_invalida_da_422(client, cotizacion_analizada):
    r = client.post(f"/cotizaciones/{cotizacion_analizada['id']}/items",
                    json={"nombre": "Algo", "horas_probable": 10, "distribucion": {"Backend": 0.5}})
    assert r.status_code == 422


def test_item_manual_sobrevive_a_reanalizar(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/items", json={"nombre": "Capacitación", "horas_probable": 12})
    r = client.post(f"/cotizaciones/{cid}/analizar").json()
    assert "Capacitación" in [i["nombre"] for i in r["items"]]


def test_editar_item_de_ia_lo_vuelve_manual(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    item = next(i for i in cotizacion_analizada["items"] if i["origen"] == "ia" and i["categoria"] != "Cross-cutting")
    r = client.put(f"/cotizaciones/{cid}/items/{item['id']}", json={"horas_probable": item["horas_probable"] + 50})
    assert r.status_code == 200
    editado = next(i for i in r.json()["items"] if i["id"] == item["id"])
    assert editado["origen"] == "manual" and editado["horas_probable"] == item["horas_probable"] + 50
    assert r.json()["total"] > cotizacion_analizada["total"]
    r = client.post(f"/cotizaciones/{cid}/analizar").json()
    assert any(i["id"] == item["id"] for i in r["items"])


def test_eliminar_item_recalcula(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    item = next(i for i in cotizacion_analizada["items"] if i["categoria"] != "Cross-cutting")
    r = client.delete(f"/cotizaciones/{cid}/items/{item['id']}")
    assert r.status_code == 200 and r.json()["total"] < cotizacion_analizada["total"]


def test_item_de_otra_cotizacion_da_404(client, cotizacion_analizada):
    assert client.delete(f"/cotizaciones/{cotizacion_analizada['id']}/items/9999").status_code == 404


def test_item_sin_tarifa_hace_rollback(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    tarifa = next(t for t in client.get("/tarifas").json() if t["rol"] == "DevOps")
    client.delete(f"/tarifas/{tarifa['id']}")
    r = client.post(f"/cotizaciones/{cid}/items", json={"nombre": "Extra", "horas_probable": 10})
    assert r.status_code == 409
    assert len(client.get(f"/cotizaciones/{cid}/items").json()) == len(cotizacion_analizada["items"])
