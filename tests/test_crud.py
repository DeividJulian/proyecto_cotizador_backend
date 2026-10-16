from tests.conftest import TARIFAS


def test_cuenta_nueva_arranca_con_tarifas_de_mercado(client):
    tarifas = client.get("/tarifas").json()
    assert {t["rol"]: t["valor_hora"] for t in tarifas} == TARIFAS
    assert client.get("/tarifas/mercado").json()[0] == {"rol": "Backend", "valor_hora": TARIFAS["Backend"]}


def test_tarifas_crud(client):
    backend = next(t for t in client.get("/tarifas").json() if t["rol"] == "Backend")
    assert client.put(f"/tarifas/{backend['id']}", json={"rol": "Backend", "valor_hora": 80000}).json()["valor_hora"] == 80000
    assert client.post("/tarifas", json={"rol": "backend", "valor_hora": 1}).status_code == 409
    r = client.post("/tarifas", json={"rol": "Data Science", "valor_hora": 90000})
    assert r.status_code == 201
    assert client.delete(f"/tarifas/{r.json()['id']}").status_code == 200
    assert len(client.get("/tarifas").json()) == len(TARIFAS)


def test_restablecer_tarifas_de_mercado(client):
    backend = next(t for t in client.get("/tarifas").json() if t["rol"] == "Backend")
    client.put(f"/tarifas/{backend['id']}", json={"rol": "Backend", "valor_hora": 99000})
    client.post("/tarifas", json={"rol": "Data Science", "valor_hora": 90000})
    r = client.post("/tarifas/restablecer")
    assert r.status_code == 200 and {t["rol"]: t["valor_hora"] for t in r.json()} == TARIFAS


def test_tarifa_invalida(client):
    assert client.post("/tarifas", json={"rol": "Research", "valor_hora": 0}).status_code == 422
