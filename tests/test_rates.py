from tests.conftest import RATES


def test_a_new_account_starts_with_market_rates(client):
    assert {r["role"]: r["hourly_rate"] for r in client.get("/rates").json()} == RATES
    assert client.get("/rates/market").json()[0] == {"role": "Backend", "hourly_rate": RATES["Backend"]}
    assert "Diseño UX/UI" in RATES and "Gestión de proyecto" in RATES


def test_rates_crud(client):
    backend = next(r for r in client.get("/rates").json() if r["role"] == "Backend")
    assert client.put(f"/rates/{backend['id']}", json={"role": "Backend", "hourly_rate": 80000}).json()["hourly_rate"] == 80000
    r = client.post("/rates", json={"role": "backend", "hourly_rate": 1})
    assert r.status_code == 409 and r.json()["detail"] == "Ya tienes una tarifa para ese rol"
    r = client.post("/rates", json={"role": "Ciencia de datos", "hourly_rate": 90000})
    assert r.status_code == 201
    assert client.delete(f"/rates/{r.json()['id']}").json() == {"message": "Tarifa eliminada"}
    assert len(client.get("/rates").json()) == len(RATES)


def test_reset_market_rates(client):
    backend = next(r for r in client.get("/rates").json() if r["role"] == "Backend")
    client.put(f"/rates/{backend['id']}", json={"role": "Backend", "hourly_rate": 99000})
    client.post("/rates", json={"role": "Ciencia de datos", "hourly_rate": 90000})
    r = client.post("/rates/reset")
    assert r.status_code == 200 and {x["role"]: x["hourly_rate"] for x in r.json()} == RATES


def test_invalid_rate(client):
    r = client.post("/rates", json={"role": "Investigación", "hourly_rate": 0})
    assert r.status_code == 422 and r.json()["detail"].startswith("Datos inválidos")
