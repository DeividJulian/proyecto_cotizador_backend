from tests.conftest import delete_rates


def test_empty_stats(client):
    r = client.get("/stats").json()
    assert r["total_quotes"] == 0 and r["close_rate_pct"] is None and r["average_ticket"] == 0


def test_examples_load_consistent_data(client):
    r = client.post("/seed")
    assert r.status_code == 200 and r.json() == {"message": "Cotizaciones de ejemplo cargadas", "summary": {"quotes": 4}}
    stats = client.get("/stats").json()
    assert stats["by_status"] == {"draft": 1, "sent": 1, "accepted": 1, "rejected": 1}
    assert stats["close_rate_pct"] == 50.0
    assert stats["accepted_value"] > 0 and stats["top_modules"]


def test_examples_are_not_duplicated_without_reset(client):
    client.post("/seed")
    r = client.post("/seed")
    assert r.status_code == 409 and "reset=true" in r.json()["detail"]
    assert client.post("/seed?reset=true").status_code == 200
    assert len(client.get("/quotes").json()) == 4


def test_examples_have_proposals_once_sent(client):
    client.post("/seed")
    for q in client.get("/quotes").json():
        detail = client.get(f"/quotes/{q['id']}").json()
        assert (detail["proposal"] is not None) == (q["status"] != "draft")


def test_examples_without_rates_return_409_and_save_nothing(client):
    delete_rates(client)
    assert client.post("/seed").status_code == 409
    assert client.get("/quotes").json() == []


def test_stats_and_examples_belong_to_each_user(client, other):
    client.post("/seed")
    assert other.get("/stats").json()["total_quotes"] == 0
    assert other.post("/seed").status_code == 200  # Luis can load his own as well
    client.post("/seed?reset=true")
    assert len(other.get("/quotes").json()) == 4  # resetting Ana's does not touch Luis's
