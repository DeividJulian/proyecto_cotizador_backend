def test_propuesta_requiere_analisis(client, cotizacion):
    assert client.post(f"/cotizaciones/{cotizacion['id']}/propuesta").status_code == 409
    assert client.get(f"/cotizaciones/{cotizacion['id']}/propuesta").status_code == 404


def test_generar_propuesta_con_secciones_y_formato_cop(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    r = client.post(f"/cotizaciones/{cid}/propuesta")
    assert r.status_code == 200
    texto = r.json()["propuesta"]
    for seccion in ["Executive summary", "Scope", "Deliverables", "Schedule", "Investment",
                    "Payment terms", "Assumptions", "Validity"]:
        assert seccion in texto
    total = f"{cotizacion_analizada['total']:,}"
    assert f"${total} COP" in texto
    assert f"QT-{cid:04d}" in texto


def test_descargar_propuesta(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/propuesta")
    r = client.get(f"/cotizaciones/{cid}/propuesta/descargar")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert r.headers["content-type"].startswith("text/markdown")


def test_no_se_puede_enviar_sin_propuesta(client, cotizacion_analizada):
    r = client.post(f"/cotizaciones/{cotizacion_analizada['id']}/estado", json={"estado": "enviada"})
    assert r.status_code == 409


def test_flujo_completo_hasta_aceptada(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/propuesta")
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"}).json()["estado"] == "enviada"
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "aceptada"}).json()["estado"] == "aceptada"


def test_transicion_invalida(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    r = client.post(f"/cotizaciones/{cid}/estado", json={"estado": "aceptada"})
    assert r.status_code == 409
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "inventado"}).status_code == 422


def test_estado_final_no_cambia(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/propuesta")
    client.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"})
    client.post(f"/cotizaciones/{cid}/estado", json={"estado": "rechazada"})
    assert client.post(f"/cotizaciones/{cid}/estado", json={"estado": "borrador"}).status_code == 409


def test_cotizacion_enviada_queda_congelada(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/propuesta")
    client.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"})
    assert client.put(f"/cotizaciones/{cid}", json={"margen_pct": 5}).status_code == 409
    assert client.post(f"/cotizaciones/{cid}/analizar").status_code == 409
    assert client.post(f"/cotizaciones/{cid}/items", json={"nombre": "Extra", "horas_probable": 5}).status_code == 409
    assert client.delete(f"/cotizaciones/{cid}").status_code == 409
    assert client.post(f"/cotizaciones/{cid}/propuesta").status_code == 409


def test_enviada_puede_volver_a_borrador_para_editar(client, cotizacion_analizada):
    cid = cotizacion_analizada["id"]
    client.post(f"/cotizaciones/{cid}/propuesta")
    client.post(f"/cotizaciones/{cid}/estado", json={"estado": "enviada"})
    client.post(f"/cotizaciones/{cid}/estado", json={"estado": "borrador"})
    assert client.put(f"/cotizaciones/{cid}", json={"margen_pct": 35}).status_code == 200
