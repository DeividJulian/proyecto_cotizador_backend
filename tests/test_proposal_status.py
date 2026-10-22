def test_the_proposal_needs_an_analysis(client, quote):
    assert client.post(f"/quotes/{quote['id']}/proposal").status_code == 409
    r = client.get(f"/quotes/{quote['id']}/proposal")
    assert r.status_code == 404 and r.json()["detail"] == "Esta cotización aún no tiene propuesta"


def test_proposal_has_its_sections_in_spanish_and_cop_format(client, analyzed_quote):
    qid = analyzed_quote["id"]
    r = client.post(f"/quotes/{qid}/proposal")
    assert r.status_code == 200
    text = r.json()["proposal"]
    for section in ["Resumen ejecutivo", "Alcance", "Entregables", "Cronograma", "Inversión",
                    "Condiciones de pago", "Supuestos", "Vigencia"]:
        assert section in text
    total = f"{analyzed_quote['total']:,}".replace(",", ".")
    assert f"${total} COP" in text
    assert f"COT-{qid:04d}" in text
    assert "**Cliente:** Ana Pérez · Pyme SAS" in text and "**Preparada por:** Ana Pérez" in text


def test_download_proposal(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/proposal")
    r = client.get(f"/quotes/{qid}/proposal/download")
    assert r.status_code == 200 and f"propuesta-COT-{qid:04d}.md" in r.headers["content-disposition"]
    assert r.headers["content-type"].startswith("text/markdown")


def test_cannot_send_without_a_proposal(client, analyzed_quote):
    r = client.post(f"/quotes/{analyzed_quote['id']}/status", json={"status": "sent"})
    assert r.status_code == 409 and "propuesta" in r.json()["detail"]


def test_full_flow_until_accepted(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/proposal")
    assert client.post(f"/quotes/{qid}/status", json={"status": "sent"}).json()["status"] == "sent"
    assert client.post(f"/quotes/{qid}/status", json={"status": "accepted"}).json()["status"] == "accepted"


def test_invalid_transition(client, analyzed_quote):
    qid = analyzed_quote["id"]
    r = client.post(f"/quotes/{qid}/status", json={"status": "accepted"})
    assert r.status_code == 409 and "No se puede pasar de borrador a aceptada" in r.json()["detail"]
    assert client.post(f"/quotes/{qid}/status", json={"status": "invented"}).status_code == 422


def test_a_final_status_does_not_change(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/proposal")
    client.post(f"/quotes/{qid}/status", json={"status": "sent"})
    client.post(f"/quotes/{qid}/status", json={"status": "rejected"})
    r = client.post(f"/quotes/{qid}/status", json={"status": "draft"})
    assert r.status_code == 409 and "estado final" in r.json()["detail"]


def test_a_sent_quote_is_frozen(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/proposal")
    client.post(f"/quotes/{qid}/status", json={"status": "sent"})
    r = client.put(f"/quotes/{qid}", json={"margin_pct": 5})
    assert r.status_code == 409 and "solo se edita en borrador" in r.json()["detail"]
    assert client.post(f"/quotes/{qid}/analyze").status_code == 409
    assert client.post(f"/quotes/{qid}/items", json={"name": "Extra", "hours_likely": 5}).status_code == 409
    assert client.delete(f"/quotes/{qid}").status_code == 409
    assert client.post(f"/quotes/{qid}/proposal").status_code == 409


def test_a_sent_quote_can_go_back_to_draft(client, analyzed_quote):
    qid = analyzed_quote["id"]
    client.post(f"/quotes/{qid}/proposal")
    client.post(f"/quotes/{qid}/status", json={"status": "sent"})
    client.post(f"/quotes/{qid}/status", json={"status": "draft"})
    assert client.put(f"/quotes/{qid}", json={"margin_pct": 35}).status_code == 200
