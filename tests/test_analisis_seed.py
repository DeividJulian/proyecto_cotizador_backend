def test_estadisticas_vacias(client):
    r = client.get("/estadisticas").json()
    assert r["total_cotizaciones"] == 0 and r["tasa_cierre_pct"] is None and r["ticket_promedio"] == 0


def test_seed_carga_datos_coherentes(client):
    r = client.post("/seed")
    assert r.status_code == 200
    assert r.json()["resumen"] == {"tarifas": 6, "clientes": 3, "cotizaciones": 4}
    est = client.get("/estadisticas").json()
    assert est["por_estado"] == {"borrador": 1, "enviada": 1, "aceptada": 1, "rechazada": 1}
    assert est["tasa_cierre_pct"] == 50.0
    assert est["valor_aceptado"] > 0 and est["modulos_mas_cotizados"]


def test_seed_no_duplica_sin_reiniciar(client):
    client.post("/seed")
    assert client.post("/seed").status_code == 409
    assert client.post("/seed?reiniciar=true").status_code == 200
    assert len(client.get("/cotizaciones").json()) == 4


def test_seed_deja_propuestas_en_enviadas(client):
    client.post("/seed")
    for c in client.get("/cotizaciones").json():
        detalle = client.get(f"/cotizaciones/{c['id']}").json()
        assert (detalle["propuesta"] is not None) == (c["estado"] != "borrador")
