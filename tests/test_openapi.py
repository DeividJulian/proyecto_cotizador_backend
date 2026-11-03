"""The OpenAPI contract: every endpoint declares its response and error schemas."""
from main import app

PLAIN_TEXT = {("get", "/quotes/{quote_id}/proposal/download")}


def operations():
    for path, methods in app.openapi()["paths"].items():
        for method, operation in methods.items():
            yield method, path, operation


def test_every_json_endpoint_declares_its_response_schema():
    missing = []
    for method, path, operation in operations():
        if (method, path) in PLAIN_TEXT:
            continue
        ok = next(r for code, r in operation["responses"].items() if code.startswith("2"))
        schema = ok.get("content", {}).get("application/json", {}).get("schema", {})
        if not schema or schema == {"type": "object"} or schema.get("additionalProperties") is True:
            missing.append(f"{method.upper()} {path}")
    assert missing == [], f"Sin response_model: {missing}"


def test_errors_use_the_error_schema():
    for method, path, operation in operations():
        for code, response in operation["responses"].items():
            if code.startswith(("4", "5")):
                schema = response["content"]["application/json"]["schema"]
                assert schema == {"$ref": "#/components/schemas/Error"}, f"{method.upper()} {path} {code}"


def test_protected_endpoints_declare_the_jwt():
    public = {"/", "/health", "/auth/register", "/auth/login", "/auth/verify", "/rates/market"}
    for method, path, operation in operations():
        if path not in public:
            assert operation.get("security") == [{"HTTPBearer": []}], f"{method.upper()} {path}"
            assert "401" in operation["responses"], f"{method.upper()} {path}"


def test_versioned_contract_is_up_to_date():
    """openapi.json is the contract the front is generated from: it must match what the app publishes."""
    import json
    from pathlib import Path

    saved = json.loads((Path(__file__).resolve().parent.parent / "openapi.json").read_text(encoding="utf-8"))
    assert saved == app.openapi(), "openapi.json está desactualizado: corre python scripts/export_openapi.py"
