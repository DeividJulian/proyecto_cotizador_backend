from services.catalog import CROSS_CUTTING, MODULES
from services.estimation import build_items, pert, summarize_estimate
from services.scope import analyze_scope
from tests.conftest import SCOPE


def keys(text):
    return {m["key"] for m in analyze_scope(text)["modules"]}


def test_catalog_splits_add_up_to_one():
    for key, module in MODULES.items():
        assert abs(sum(module["split"].values()) - 1) < 1e-9, key


def test_detects_the_modules_of_the_scope():
    assert {"authentication", "catalog", "payments", "admin_panel", "reports"} <= keys(SCOPE)


def test_detects_modules_in_english_descriptions():
    text = "We need an online store with a product catalog, shopping cart, online payments and an admin panel."
    assert {"catalog", "payments", "admin_panel"} <= keys(text)
    assert {"mobile", "authentication", "notifications"} <= keys("A mobile app where users sign up and get email notifications")


def test_ignores_accents_and_upper_case():
    assert "authentication" in keys("NECESITAMOS INICIO DE SESIÓN y permisos para el equipo")


def test_vague_scope_detects_nothing_and_warns():
    result = analyze_scope("Quiero algo bonito para mi negocio de verdad")
    assert result["modules"] == [] and result["warnings"]
    assert "módulo" in " ".join(result["warnings"])


def test_high_complexity_signal():
    result = analyze_scope("Un sistema de reportes complejo con tablero de indicadores")
    assert next(m for m in result["modules"] if m["key"] == "reports")["complexity"] == "high"
    result = analyze_scope("Advanced reports with real-time charts for thousands of users")
    assert next(m for m in result["modules"] if m["key"] == "reports")["complexity"] == "high"


def test_low_complexity_signal():
    result = analyze_scope("Un sitio web institucional sencillo para la empresa")
    module = next(m for m in result["modules"] if m["key"] == "website")
    assert module["complexity"] == "low" and "sencillo" in module["reasons"]


def test_module_names_are_shown_in_spanish():
    names = {m["name"] for m in analyze_scope(SCOPE)["modules"]}
    assert "Panel administrativo" in names and "Carrito de compras y pagos en línea" in names


def test_pert_formula():
    assert pert(6, 12, 24) == (6 + 48 + 24) / 6


def test_high_complexity_costs_more_than_low():
    base = {"key": "payments", "name": "Pagos", "category": "Negocio", "reasons": ""}
    low = build_items([{**base, "complexity": "low"}])[0]
    high = build_items([{**base, "complexity": "high"}])[0]
    assert high["hours_expected"] > low["hours_expected"]
    assert low["hours_optimistic"] < low["hours_likely"] < low["hours_pessimistic"]


def test_cross_cutting_work_is_added_with_a_minimum():
    items = build_items([{"key": "website", "name": "Sitio", "category": "Contenido", "complexity": "low", "reasons": ""}])
    cross_cutting = [i for i in items if i["category"] == CROSS_CUTTING]
    assert len(cross_cutting) == 3
    assert all(i["hours_likely"] >= 8 for i in cross_cutting)


def test_summary_adds_the_hours_by_role():
    items = build_items(analyze_scope(SCOPE)["modules"])
    result = summarize_estimate(items)
    roles_total = round(sum(r["expected"] for r in result["by_role"].values()), 1)
    assert abs(result["hours_expected"] - roles_total) < 0.2
    assert result["hours_optimistic"] < result["hours_expected"] < result["hours_pessimistic"]


def test_analyze_and_estimate_endpoints(client):
    r = client.post("/scope/analyze", json={"scope_description": SCOPE})
    assert r.status_code == 200 and r.json()["modules"]
    r = client.post("/scope/estimate", json={"scope_description": SCOPE})
    assert r.status_code == 200 and r.json()["estimate"]["hours_expected"] > 0


def test_estimating_a_vague_scope_returns_422(client):
    r = client.post("/scope/estimate", json={"scope_description": "Quiero algo bonito para mi negocio"})
    assert r.status_code == 422
