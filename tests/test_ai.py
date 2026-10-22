"""AI features with Groq simulated at the HTTP level: no test ever calls the real provider."""
import json

import httpx
import pytest

from services import llm

SCOPE_REVIEW = {
    "suggestions": [
        {"key": "notifications", "reason": "Los clientes reciben la confirmación del pedido por correo."},
        {"key": "notifications", "reason": "Repetida."},
        {"key": "catalog", "reason": "Ya está en la cotización."},
    ],
    "missing_details": ["¿Cuántos productos tendrá el catálogo?"],
}
EXPLANATION = {
    "summary": "El precio sale de las horas por rol multiplicadas por tus tarifas.",
    "drivers": ["El carrito y los pagos son los módulos más pesados."],
    "ways_to_lower": ["Dejar los reportes para una segunda fase."],
}
QUESTIONS = {
    "questions": ["¿Qué pasarela de pagos usa [empresa]?", "¿Quién carga los productos?"],
    "risks": [{"risk": "La pasarela tarda en aprobar la cuenta.", "mitigation": "Pedir los accesos desde el inicio."}],
}


@pytest.fixture
def groq(monkeypatch):
    """Fake Groq API. Set `reply` (dict, raw text, or a list of (status, body, headers) answered in order)."""
    state = {"reply": SCOPE_REVIEW, "requests": [], "finish_reason": "stop", "message": {}}

    def handler(request: httpx.Request) -> httpx.Response:
        state["requests"].append({"url": str(request.url), "headers": request.headers, "body": json.loads(request.content)})
        reply = state["reply"]
        if isinstance(reply, list):
            status, body, headers = reply.pop(0)
            if status == "timeout":
                raise httpx.ReadTimeout("slow", request=request)
            if status == 200:
                body = {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": json.dumps(body)}}]}
            return httpx.Response(status, json=body, headers=headers or {})
        content = reply if isinstance(reply, str) else json.dumps(reply)
        message = {"role": "assistant", "content": content, **state["message"]}
        return httpx.Response(200, json={"choices": [{"finish_reason": state["finish_reason"], "message": message}]})

    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("AI_API_KEY", "gsk_test-key")
    monkeypatch.setenv("AI_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setattr(llm, "RETRY_DELAY_SECONDS", 0)
    monkeypatch.setattr(llm, "_http", httpx.Client(transport=httpx.MockTransport(handler)))
    return state


def sent_text(groq) -> str:
    return json.dumps([r["body"] for r in groq["requests"]], ensure_ascii=False)


# ---------- Status and configuration ----------

def test_status_without_key(client):
    assert client.get("/ai/status").json() == {"configured": False, "provider": "groq", "model": "openai/gpt-oss-20b"}


def test_status_with_key(client, groq):
    assert client.get("/ai/status").json() == {"configured": True, "provider": "groq", "model": "openai/gpt-oss-20b"}


def test_status_requires_login(anonymous):
    assert anonymous.get("/ai/status").status_code == 401


@pytest.mark.parametrize("path", ["scope-review", "explain-price", "client-questions", "improve-proposal"])
def test_every_feature_requires_login(anonymous, path):
    assert anonymous.post(f"/ai/quotes/1/{path}").status_code == 401


def test_without_key_returns_503(client, analyzed_quote):
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 503
    assert r.json()["detail"].startswith("La IA no está configurada")


def test_unknown_provider_returns_503(client, analyzed_quote, groq, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "otra")
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 503
    assert groq["requests"] == []


# ---------- What is sent to Groq ----------

def test_request_to_groq(client, analyzed_quote, groq):
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 200
    sent = groq["requests"][0]
    assert sent["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert sent["headers"]["authorization"] == "Bearer gsk_test-key"
    body = sent["body"]
    assert body["model"] == "openai/gpt-oss-20b"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    response_format = body["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True
    schema = response_format["json_schema"]["schema"]
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_no_personal_data_reaches_the_model(client, groq):
    quote = client.post("/quotes", json={
        "title": "Tienda para Café La Montaña",
        "scope_description": (
            "Laura Gómez de Café La Montaña quiere una tienda en línea con catálogo de productos y pagos en línea. "
            "Contacto: laura@cafe.co o +57 300 123 4567. Lo desarrolla Ana Pérez (ana@pyme.com)."
        ),
        "client_name": "Laura Gómez",
        "client_company": "Café La Montaña",
    }).json()
    client.post(f"/quotes/{quote['id']}/analyze")
    groq["reply"] = QUESTIONS
    r = client.post(f"/ai/quotes/{quote['id']}/client-questions")
    assert r.status_code == 200
    text = sent_text(groq).lower()
    for private in ["laura", "gómez", "gomez", "montaña", "laura@cafe.co", "300 123 4567", "ana pérez", "pérez", "ana@pyme.com"]:
        assert private not in text, private
    assert "[cliente]" in text and "[empresa]" in text and "[correo 1]" in text
    # The placeholders in the answer go back to the real values
    assert r.json()["questions"][0] == "¿Qué pasarela de pagos usa Café La Montaña?"


# ---------- 1. Second opinion on the scope ----------

def test_scope_review_only_suggests_new_catalog_modules(client, analyzed_quote, groq):
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 200
    body = r.json()
    assert [s["key"] for s in body["suggestions"]] == ["notifications"]
    suggestion = body["suggestions"][0]
    assert suggestion["name"] == "Notificaciones por correo, SMS o WhatsApp"
    assert suggestion["hours_likely"] > 0 and abs(sum(suggestion["split"].values()) - 1) < 1e-6
    assert body["missing_details"] == ["¿Cuántos productos tendrá el catálogo?"]
    # The catalog sent to the model leaves out the modules already in the quote
    assert '"key": "catalog"' not in groq["requests"][0]["body"]["messages"][1]["content"]


def test_a_suggestion_can_be_added_as_a_manual_item(client, analyzed_quote, groq):
    suggestion = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").json()["suggestions"][0]
    r = client.post(f"/quotes/{analyzed_quote['id']}/items", json={
        "name": suggestion["name"], "category": suggestion["category"], "hours_likely": suggestion["hours_likely"],
        "split": suggestion["split"],
    })
    assert r.status_code == 201
    added = next(i for i in r.json()["items"] if i["name"] == suggestion["name"])
    assert added["source"] == "manual"


def test_module_outside_the_catalog_returns_502(client, analyzed_quote, groq):
    groq["reply"] = {"suggestions": [{"key": "blockchain", "reason": "x"}], "missing_details": []}
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 502 and "válida" in r.json()["detail"]


# ---------- 2. Price explanation ----------

def test_explain_price_keeps_the_numbers(client, analyzed_quote, groq):
    groq["reply"] = EXPLANATION
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/explain-price")
    assert r.status_code == 200
    assert r.json()["drivers"] == EXPLANATION["drivers"]
    user_message = groq["requests"][0]["body"]["messages"][1]["content"]
    assert "COP" in user_message  # the model receives our amounts already written
    after = client.get(f"/quotes/{analyzed_quote['id']}").json()
    assert after["total"] == analyzed_quote["total"] and after["items"] == analyzed_quote["items"]


def test_explain_price_needs_an_analyzed_quote(client, quote, groq):
    r = client.post(f"/ai/quotes/{quote['id']}/explain-price")
    assert r.status_code == 409
    assert groq["requests"] == []


# ---------- 3. Questions and risks ----------

def test_client_questions(client, analyzed_quote, groq):
    groq["reply"] = QUESTIONS
    body = client.post(f"/ai/quotes/{analyzed_quote['id']}/client-questions").json()
    assert body["questions"][1] == "¿Quién carga los productos?"
    assert body["risks"] == QUESTIONS["risks"]


# ---------- 4. Proposal wording ----------

@pytest.fixture
def proposal(client, analyzed_quote):
    r = client.post(f"/quotes/{analyzed_quote['id']}/proposal")
    assert r.status_code == 200
    return r.json()["proposal"]


def _section(proposal: str, title: str) -> tuple[str, str]:
    from services.proposal import section_title, split_sections
    return next((h, b.strip()) for h, b in split_sections(proposal)[1] if section_title(h) == title)


def test_improve_proposal_discards_changed_numbers(client, analyzed_quote, proposal, groq):
    summary_heading, summary = _section(proposal, "Resumen ejecutivo")
    _, assumptions = _section(proposal, "Supuestos y exclusiones")
    groq["reply"] = {"sections": [
        {"index": 0, "text": "Con gusto presento " + summary[len("Presentamos "):]},  # same figures
        {"index": 2, "text": assumptions.replace("3 días", "5 días")},  # changes a figure
    ]}
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/improve-proposal")
    assert r.status_code == 200
    body = r.json()
    assert [s["heading"] for s in body["sections"]] == [summary_heading]
    assert body["sections"][0]["original"] == summary
    assert body["discarded"] == ["7. Supuestos y exclusiones"]
    # Nothing is saved until the user applies it
    assert client.get(f"/quotes/{analyzed_quote['id']}/proposal").json()["proposal"] == proposal


def test_apply_improved_sections(client, analyzed_quote, proposal):
    heading, summary = _section(proposal, "Resumen ejecutivo")
    new_text = "Con gusto presento " + summary[len("Presentamos "):]
    r = client.patch(f"/quotes/{analyzed_quote['id']}/proposal", json={"sections": [{"heading": heading, "text": new_text}]})
    assert r.status_code == 200
    saved = r.json()["proposal"]
    assert new_text in saved and summary not in saved
    assert saved.replace(new_text, summary) == proposal  # the rest of the document is untouched


def test_apply_rejects_changed_numbers(client, analyzed_quote, proposal):
    heading, summary = _section(proposal, "Resumen ejecutivo")
    r = client.patch(f"/quotes/{analyzed_quote['id']}/proposal",
                     json={"sections": [{"heading": heading, "text": summary + " Entrega en 2 semanas."}]})
    assert r.status_code == 409 and "cifras" in r.json()["detail"]


def test_apply_unknown_section(client, analyzed_quote, proposal):
    r = client.patch(f"/quotes/{analyzed_quote['id']}/proposal", json={"sections": [{"heading": "9. Otra", "text": "x"}]})
    assert r.status_code == 404


def test_apply_only_on_drafts(client, analyzed_quote, proposal):
    heading, summary = _section(proposal, "Resumen ejecutivo")
    assert client.post(f"/quotes/{analyzed_quote['id']}/status", json={"status": "sent"}).status_code == 200
    r = client.patch(f"/quotes/{analyzed_quote['id']}/proposal", json={"sections": [{"heading": heading, "text": summary}]})
    assert r.status_code == 409


def test_improve_needs_a_proposal(client, analyzed_quote, groq):
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/improve-proposal").status_code == 409
    assert groq["requests"] == []


# ---------- Isolation ----------

@pytest.mark.parametrize("path", ["scope-review", "explain-price", "client-questions", "improve-proposal"])
def test_another_users_quote_is_not_found(other, analyzed_quote, groq, path):
    assert other.post(f"/ai/quotes/{analyzed_quote['id']}/{path}").status_code == 404
    assert groq["requests"] == []


# ---------- Provider errors: never a 500 ----------

def test_invalid_json_returns_502(client, analyzed_quote, groq):
    groq["reply"] = "esto no es JSON"
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 502 and "válida" in r.json()["detail"]


def test_missing_field_returns_502(client, analyzed_quote, groq):
    groq["reply"] = {"suggestions": []}
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 502


def test_json_inside_a_code_fence_is_accepted(client, analyzed_quote, groq):
    groq["reply"] = "```json\n" + json.dumps(SCOPE_REVIEW) + "\n```"
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 200


def test_refusal_returns_502(client, analyzed_quote, groq):
    groq["message"] = {"refusal": "No puedo ayudar con eso"}
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 502


def test_rate_limit_returns_429_with_retry_after(client, analyzed_quote, groq):
    groq["reply"] = [(429, {"error": "rate limit"}, {"retry-after": "12"})]
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 429
    assert r.headers["retry-after"] == "12"
    assert "límite" in r.json()["detail"]
    assert len(groq["requests"]) == 1  # usage limits are not retried


def test_server_error_is_retried_once(client, analyzed_quote, groq):
    groq["reply"] = [(503, {"error": "busy"}, None), (200, SCOPE_REVIEW, None)]
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 200
    assert len(groq["requests"]) == 2


def test_provider_down_returns_502(client, analyzed_quote, groq):
    groq["reply"] = [(500, {}, None), (500, {}, None)]
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 502 and "no está disponible" in r.json()["detail"]
    assert len(groq["requests"]) == 2


def test_bad_key_returns_502(client, analyzed_quote, groq):
    groq["reply"] = [(401, {"error": "invalid key"}, None)]
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 502 and "AI_API_KEY" in r.json()["detail"]
    assert "gsk_test-key" not in r.text


def test_timeout_returns_502(client, analyzed_quote, groq):
    groq["reply"] = [("timeout", None, None)]
    r = client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review")
    assert r.status_code == 502 and "tardó demasiado" in r.json()["detail"]


def test_fallback_model_answers_when_the_main_one_is_busy(client, analyzed_quote, groq, monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_MODEL", "llama-3.1-8b-instant")
    groq["reply"] = [(503, {"error": "busy"}, None), (200, SCOPE_REVIEW, None)]
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 200
    assert [r["body"]["model"] for r in groq["requests"]] == ["openai/gpt-oss-20b", "llama-3.1-8b-instant"]


def test_fallback_after_a_timeout(client, analyzed_quote, groq, monkeypatch):
    monkeypatch.setenv("AI_FALLBACK_MODEL", "llama-3.1-8b-instant")
    groq["reply"] = [("timeout", None, None), (200, SCOPE_REVIEW, None)]
    assert client.post(f"/ai/quotes/{analyzed_quote['id']}/scope-review").status_code == 200
    assert groq["requests"][1]["body"]["model"] == "llama-3.1-8b-instant"


# ---------- Privacy helper ----------

def test_redactor_hides_and_restores():
    from services.privacy import Redactor
    redactor = Redactor({"[cliente]": "Sebastián Ortiz"}, emails=("seb@x.co",))
    text = "Sebastian Ortiz (seb@x.co, 3001234567) paga $13.613.600 COP en 2025-2026."
    hidden = redactor.redact(text)
    assert hidden == "[cliente] ([correo 1], [teléfono 1]) paga $13.613.600 COP en 2025-2026."
    assert redactor.restore(hidden) == "Sebastián Ortiz (seb@x.co, 3001234567) paga $13.613.600 COP en 2025-2026."
