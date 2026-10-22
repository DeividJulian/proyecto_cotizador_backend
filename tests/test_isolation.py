"""Every user sees and changes only their own data: quotes, items, proposals, rates and stats."""
import pytest

from tests.conftest import SCOPE

PRIVATE_ROUTES = [
    ("get", "/quotes"),
    ("post", "/quotes"),
    ("get", "/quotes/1"),
    ("put", "/quotes/1"),
    ("delete", "/quotes/1"),
    ("post", "/quotes/1/analyze"),
    ("get", "/quotes/1/summary"),
    ("post", "/quotes/1/status"),
    ("get", "/quotes/1/similar"),
    ("get", "/quotes/1/items"),
    ("post", "/quotes/1/items"),
    ("get", "/quotes/1/proposal"),
    ("post", "/quotes/1/proposal"),
    ("get", "/rates"),
    ("post", "/rates"),
    ("post", "/rates/reset"),
    ("post", "/scope/estimate"),
    ("post", "/finance/simulate"),
    ("get", "/stats"),
    ("post", "/seed"),
]


def call(session, method, path):
    return getattr(session, method)(path, **({"json": {}} if method in ("post", "put") else {}))


@pytest.mark.parametrize("method,path", PRIVATE_ROUTES)
def test_without_a_session_it_returns_401(anonymous, method, path):
    assert call(anonymous, method, path).status_code == 401


def test_public_routes_need_no_session(anonymous):
    assert anonymous.get("/").status_code == 200
    assert anonymous.get("/health").status_code == 200
    assert anonymous.get("/rates/market").status_code == 200


def test_another_user_cannot_see_or_touch_my_quotes(analyzed_quote, other):
    qid = analyzed_quote["id"]
    assert other.get("/quotes").json() == []
    for method, path in [
        ("get", f"/quotes/{qid}"),
        ("get", f"/quotes/{qid}/summary"),
        ("put", f"/quotes/{qid}"),
        ("delete", f"/quotes/{qid}"),
        ("post", f"/quotes/{qid}/analyze"),
        ("get", f"/quotes/{qid}/items"),
        ("post", f"/quotes/{qid}/proposal"),
        ("get", f"/quotes/{qid}/proposal"),
        ("get", f"/quotes/{qid}/similar"),
    ]:
        assert call(other, method, path).status_code == 404, path
    assert other.post(f"/quotes/{qid}/status", json={"status": "sent"}).status_code == 404


def test_another_user_cannot_touch_my_items(client, analyzed_quote, other):
    qid = analyzed_quote["id"]
    item = analyzed_quote["items"][0]
    assert other.delete(f"/quotes/{qid}/items/{item['id']}").status_code == 404
    assert other.put(f"/quotes/{qid}/items/{item['id']}", json={"hours_likely": 1}).status_code == 404
    assert len(client.get(f"/quotes/{qid}/items").json()) == len(analyzed_quote["items"])


def test_rates_belong_to_each_user(client, other):
    mine = next(r for r in client.get("/rates").json() if r["role"] == "Backend")
    assert other.put(f"/rates/{mine['id']}", json={"role": "Backend", "hourly_rate": 1}).status_code == 404
    assert other.delete(f"/rates/{mine['id']}").status_code == 404
    client.put(f"/rates/{mine['id']}", json={"role": "Backend", "hourly_rate": 120000})
    luis = next(r for r in other.get("/rates").json() if r["role"] == "Backend")
    assert luis["hourly_rate"] != 120000
    # each one can have their own "Ciencia de datos"
    assert client.post("/rates", json={"role": "Ciencia de datos", "hourly_rate": 90000}).status_code == 201
    assert other.post("/rates", json={"role": "Ciencia de datos", "hourly_rate": 70000}).status_code == 201


def test_the_price_uses_the_owners_rates(client, other):
    body = {"title": "Tienda", "scope_description": SCOPE}
    mine = client.post("/quotes", json=body).json()
    luis = other.post("/quotes", json=body).json()
    for rate in other.get("/rates").json():  # Luis charges double
        other.put(f"/rates/{rate['id']}", json={"role": rate["role"], "hourly_rate": rate["hourly_rate"] * 2})
    my_total = client.post(f"/quotes/{mine['id']}/analyze").json()["total"]
    luis_total = other.post(f"/quotes/{luis['id']}/analyze").json()["total"]
    assert luis_total == pytest.approx(my_total * 2, rel=0.001)


def test_similar_only_compares_with_my_quotes(client, quote, other):
    other.post("/quotes", json={"title": "Tienda de Luis", "scope_description": SCOPE})
    assert client.get(f"/quotes/{quote['id']}/similar").json() == []


def test_the_user_runs_the_whole_cycle_of_their_quote(client, analyzed_quote):
    """No admin: the same user generates the proposal, sends it to their client and records the answer."""
    qid = analyzed_quote["id"]
    assert client.post(f"/quotes/{qid}/proposal").status_code == 200
    assert client.post(f"/quotes/{qid}/status", json={"status": "sent"}).status_code == 200
    assert client.post(f"/quotes/{qid}/status", json={"status": "accepted"}).json()["status"] == "accepted"
