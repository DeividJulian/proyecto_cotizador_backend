import pytest

from services.finance import MissingRate, calculate_financials
from tests.conftest import delete_rates

RATES = {"Backend": 50000, "Frontend": 40000}


def test_calculation_order_with_known_values():
    f = calculate_financials({"Backend": 100, "Frontend": 50}, RATES, margin_pct=30, contingency_pct=10)
    assert f["direct_cost"] == 7_000_000
    assert f["contingency"] == 700_000
    assert f["margin"] == 2_310_000
    assert f["subtotal"] == 10_010_000
    assert f["vat"] == 1_901_900
    assert f["total"] == 11_911_900


def test_discount_is_applied_before_vat():
    f = calculate_financials({"Backend": 100}, RATES, margin_pct=0, contingency_pct=0, discount_pct=10, vat_pct=19)
    assert f["discount"] == 500_000
    assert f["taxable_base"] == 4_500_000
    assert f["vat"] == 855_000
    assert f["total"] == 5_355_000


def test_milestones_add_up_to_the_exact_total():
    f = calculate_financials({"Backend": 77.3, "Frontend": 31.9}, RATES, margin_pct=27, contingency_pct=13)
    assert sum(m["amount"] for m in f["payment_milestones"]) == f["total"]
    assert [m["percentage"] for m in f["payment_milestones"]] == [40, 30, 30]
    assert f["payment_milestones"][0]["name"] == "Anticipo al firmar"


def test_duration_depends_on_the_busiest_role():
    f = calculate_financials({"Backend": 90, "Frontend": 10}, RATES)
    assert f["duration_weeks"] == 3  # 90 h / 30 h per week


def test_missing_rate():
    with pytest.raises(MissingRate) as e:
        calculate_financials({"Backend": 10, "QA": 5}, RATES)
    assert e.value.roles == ["QA"] and "Falta la tarifa" in str(e.value)


def test_simulate_endpoint(client, rates):
    r = client.post("/finance/simulate", json={"hours_by_role": {"Backend": 100, "Frontend": 50}})
    assert r.status_code == 200
    assert r.json()["total"] == 13_613_600


def test_simulate_without_rates_returns_409(client):
    delete_rates(client)
    r = client.post("/finance/simulate", json={"hours_by_role": {"Backend": 10}})
    assert r.status_code == 409 and "Backend" in r.json()["detail"]


def test_simulate_validates_the_parameters(client, rates):
    r = client.post("/finance/simulate", json={"hours_by_role": {"Backend": 10}, "discount_pct": 90})
    assert r.status_code == 422
