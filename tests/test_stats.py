def test_empty_stats(client):
    r = client.get("/stats").json()
    assert r["total_quotes"] == 0 and r["close_rate_pct"] is None and r["average_ticket"] == 0


def test_the_load_examples_endpoint_no_longer_exists(client):
    assert client.post("/seed").status_code in (404, 405)
