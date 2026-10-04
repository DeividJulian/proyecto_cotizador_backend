def test_raiz_y_health(client):
    assert client.get("/").status_code == 200
    assert client.get("/health").json() == {"status": "ok"}


def test_validacion_devuelve_mensaje_legible(client):
    r = client.post("/cotizaciones", json={"cliente_id": 1, "titulo": "ab", "descripcion_alcance": "corto"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


def test_alcance_demasiado_corto(client):
    assert client.post("/alcance/analizar", json={"descripcion_alcance": "hola"}).status_code == 422


def test_ruta_inexistente(client):
    assert client.get("/no-existe").status_code == 404
