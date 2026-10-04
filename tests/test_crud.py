def test_clientes_crud(client):
    r = client.post("/clientes", json={"nombre": "Ana", "email": "ana@x.com"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.get(f"/clientes/{cid}").json()["email"] == "ana@x.com"
    assert client.put(f"/clientes/{cid}", json={"nombre": "Ana María", "email": "ana@x.com"}).json()["nombre"] == "Ana María"
    assert len(client.get("/clientes").json()) == 1
    assert client.delete(f"/clientes/{cid}").status_code == 200
    assert client.get(f"/clientes/{cid}").status_code == 404


def test_cliente_email_duplicado_y_invalido(client):
    client.post("/clientes", json={"nombre": "Ana", "email": "ana@x.com"})
    assert client.post("/clientes", json={"nombre": "Otra", "email": "ana@x.com"}).status_code == 409
    assert client.post("/clientes", json={"nombre": "Luis", "email": "no-es-correo"}).status_code == 422


def test_tarifas_crud(client):
    r = client.post("/tarifas", json={"rol": "Backend", "valor_hora": 50000})
    assert r.status_code == 201
    tid = r.json()["id"]
    assert client.post("/tarifas", json={"rol": "backend", "valor_hora": 1}).status_code == 409
    assert client.put(f"/tarifas/{tid}", json={"rol": "Backend", "valor_hora": 60000}).json()["valor_hora"] == 60000
    assert client.delete(f"/tarifas/{tid}").status_code == 200
    assert client.get("/tarifas").json() == []


def test_tarifa_invalida(client):
    assert client.post("/tarifas", json={"rol": "Backend", "valor_hora": 0}).status_code == 422
