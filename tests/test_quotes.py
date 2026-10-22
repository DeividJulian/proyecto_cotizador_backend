from services.catalog import CROSS_CUTTING
from tests.conftest import RATES, delete_rates


def test_a_new_quote_is_a_draft(client, quote):
    assert quote["status"] == "draft" and quote["total"] == 0 and quote["items"] == []


def test_who_the_project_is_for_is_optional(client):
    r = client.post("/quotes", json={"title": "Proyecto X", "scope_description": "Una tienda en línea con pagos"})
    assert r.status_code == 201 and r.json()["client_name"] is None


def test_analyzing_creates_items_estimate_and_total(analyzed_quote):
    q = analyzed_quote
    assert q["items"] and q["total"] > 0
    assert q["estimate"]["hours_expected"] > 0
    assert q["financials"]["total"] == q["total"]
    assert {i["source"] for i in q["items"]} == {"ai"}
    assert any(i["category"] == CROSS_CUTTING for i in q["items"])


def test_analyzing_without_rates_returns_409_and_saves_nothing(client, quote):
    delete_rates(client)
    r = client.post(f"/quotes/{quote['id']}/analyze")
    assert r.status_code == 409 and "tarifa" in r.json()["detail"].lower()
    assert client.get(f"/quotes/{quote['id']}").json()["items"] == []


def test_analyzing_a_vague_scope_returns_422(client, rates):
    q = client.post("/quotes", json={"title": "Vago", "scope_description": "Quiero algo bonito para mi negocio"}).json()
    assert client.post(f"/quotes/{q['id']}/analyze").status_code == 422


def test_analyzing_again_does_not_duplicate_items(client, analyzed_quote):
    n = len(analyzed_quote["items"])
    assert len(client.post(f"/quotes/{analyzed_quote['id']}/analyze").json()["items"]) == n


def test_changing_the_margin_recalculates_the_total(client, analyzed_quote):
    qid = analyzed_quote["id"]
    r = client.put(f"/quotes/{qid}", json={"margin_pct": 50})
    assert r.status_code == 200 and r.json()["total"] > analyzed_quote["total"]
    r = client.put(f"/quotes/{qid}", json={"discount_pct": 10})
    assert r.json()["total"] < client.put(f"/quotes/{qid}", json={"discount_pct": 0}).json()["total"]


def test_a_rate_change_shows_up_when_recalculating(client, analyzed_quote):
    backend = next(r for r in client.get("/rates").json() if r["role"] == "Backend")
    client.put(f"/rates/{backend['id']}", json={"role": "Backend", "hourly_rate": RATES["Backend"] * 2})
    r = client.put(f"/quotes/{analyzed_quote['id']}", json={"title": "Tienda en línea v2"})
    assert r.json()["total"] > analyzed_quote["total"]


def test_summary(client, analyzed_quote):
    r = client.get(f"/quotes/{analyzed_quote['id']}/summary").json()
    assert r["client"] == "Ana Pérez" and r["total"] == analyzed_quote["total"]
    assert r["hours_range"][0] < r["hours_expected"] < r["hours_range"][1]
    assert r["has_proposal"] is False


def test_list_and_filter(client, analyzed_quote):
    assert len(client.get("/quotes").json()) == 1
    assert client.get("/quotes?status=accepted").json() == []
    assert len(client.get("/quotes?status=draft").json()) == 1


def test_deleting_a_draft_deletes_its_items(client, analyzed_quote):
    qid = analyzed_quote["id"]
    assert client.delete(f"/quotes/{qid}").json() == {"message": "Cotización eliminada"}
    assert client.get(f"/quotes/{qid}").status_code == 404


def test_missing_quote(client):
    r = client.get("/quotes/999")
    assert r.status_code == 404 and r.json()["detail"] == "Cotización no encontrada"
    assert client.post("/quotes/999/analyze").status_code == 404


def test_similar_quotes(client, rates, quote):
    client.post("/quotes", json={"title": "Otra tienda", "scope_description": "Tienda en línea con catálogo de productos y pagos en línea"})
    client.post("/quotes", json={"title": "Intranet", "scope_description": "Intranet de documentos para recursos humanos"})
    r = client.get(f"/quotes/{quote['id']}/similar").json()
    assert r[0]["title"] == "Otra tienda"
    assert r[0]["similarity"] >= r[-1]["similarity"]


def test_editing_and_clearing_who_it_is_for(client, quote):
    r = client.put(f"/quotes/{quote['id']}", json={"client_name": "Carlos", "client_company": ""})
    assert r.json()["client_name"] == "Carlos" and r.json()["client_company"] is None
