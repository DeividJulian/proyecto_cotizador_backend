def test_root_and_health(client):
    assert client.get("/").json() == {"message": "API del Cotizador IA funcionando"}
    assert client.get("/health").json() == {"status": "ok"}


def test_validation_returns_a_readable_message(client):
    r = client.post("/quotes", json={"title": "ab", "scope_description": "corto"})
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)
    assert r.json()["detail"].startswith("Datos inválidos")


def test_scope_too_short(client):
    assert client.post("/scope/analyze", json={"scope_description": "hola"}).status_code == 422


def test_missing_route(client):
    assert client.get("/no-existe").status_code == 404


def test_cors_only_allows_the_front(anonymous):
    allowed = anonymous.options(
        "/quotes", headers={"Origin": "https://cotizador-front-eight.vercel.app", "Access-Control-Request-Method": "GET"}
    )
    assert allowed.headers.get("access-control-allow-origin") == "https://cotizador-front-eight.vercel.app"
    local = anonymous.options("/quotes", headers={"Origin": "http://localhost:4200", "Access-Control-Request-Method": "GET"})
    assert local.headers.get("access-control-allow-origin") == "http://localhost:4200"
    foreign = anonymous.options("/quotes", headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in foreign.headers
