from services.catalog import CROSS_CUTTING, CUSTOM


def test_adding_a_manual_item_recalculates(client, analyzed_quote):
    qid = analyzed_quote["id"]
    r = client.post(f"/quotes/{qid}/items", json={"name": "Integración con ERP", "complexity": "high", "hours_likely": 40})
    assert r.status_code == 201
    q = r.json()
    assert q["total"] > analyzed_quote["total"]
    new = next(i for i in q["items"] if i["name"] == "Integración con ERP")
    assert new["source"] == "manual" and new["category"] == CUSTOM and new["reasons"] == "Agregado manualmente"
    assert new["hours_optimistic"] < 40 < new["hours_pessimistic"]


def test_invalid_split_returns_422(client, analyzed_quote):
    r = client.post(f"/quotes/{analyzed_quote['id']}/items",
                    json={"name": "Algo", "hours_likely": 10, "split": {"Backend": 0.5}})
    assert r.status_code == 422 and "100 %" in r.json()["detail"]


def test_a_manual_item_survives_a_new_analysis(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/items", json={"name": "Capacitación", "hours_likely": 12})
    r = client.post(f"/quotes/{qid}/analyze").json()
    assert "Capacitación" in [i["name"] for i in r["items"]]


def test_editing_an_analysis_item_turns_it_manual(client, analyzed_quote):
    qid = analyzed_quote["id"]
    item = next(i for i in analyzed_quote["items"] if i["source"] == "ai" and i["category"] != CROSS_CUTTING)
    r = client.put(f"/quotes/{qid}/items/{item['id']}", json={"hours_likely": item["hours_likely"] + 50})
    assert r.status_code == 200
    edited = next(i for i in r.json()["items"] if i["id"] == item["id"])
    assert edited["source"] == "manual" and edited["hours_likely"] == item["hours_likely"] + 50
    assert edited["reasons"] == "Ajustado manualmente"
    assert r.json()["total"] > analyzed_quote["total"]
    r = client.post(f"/quotes/{qid}/analyze").json()
    assert any(i["id"] == item["id"] for i in r["items"])


def test_deleting_an_item_recalculates(client, analyzed_quote):
    qid = analyzed_quote["id"]
    item = next(i for i in analyzed_quote["items"] if i["category"] != CROSS_CUTTING)
    r = client.delete(f"/quotes/{qid}/items/{item['id']}")
    assert r.status_code == 200 and r.json()["total"] < analyzed_quote["total"]


def test_missing_item_returns_404(client, analyzed_quote):
    r = client.delete(f"/quotes/{analyzed_quote['id']}/items/9999")
    assert r.status_code == 404 and r.json()["detail"] == "Módulo no encontrado en esta cotización"


def test_an_item_without_rate_rolls_back(client, analyzed_quote):
    qid = analyzed_quote["id"]
    rate = next(r for r in client.get("/rates").json() if r["role"] == "DevOps")
    client.delete(f"/rates/{rate['id']}")
    r = client.post(f"/quotes/{qid}/items", json={"name": "Extra", "hours_likely": 10})
    assert r.status_code == 409
    assert len(client.get(f"/quotes/{qid}/items").json()) == len(analyzed_quote["items"])
