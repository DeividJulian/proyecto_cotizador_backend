import pytest

from services.finanzas import TarifaFaltante, calcular_financiero

TARIFAS = {"Backend": 50000, "Frontend": 40000}


def test_orden_de_calculo_con_valores_conocidos():
    f = calcular_financiero({"Backend": 100, "Frontend": 50}, TARIFAS, margen_pct=30, contingencia_pct=10)
    assert f["costo_directo"] == 7_000_000
    assert f["contingencia"] == 700_000
    assert f["margen"] == 2_310_000
    assert f["subtotal"] == 10_010_000
    assert f["iva"] == 1_901_900
    assert f["total"] == 11_911_900


def test_descuento_se_aplica_antes_del_iva():
    f = calcular_financiero({"Backend": 100}, TARIFAS, margen_pct=0, contingencia_pct=0, descuento_pct=10, iva_pct=19)
    assert f["descuento"] == 500_000
    assert f["base_gravable"] == 4_500_000
    assert f["iva"] == 855_000
    assert f["total"] == 5_355_000


def test_hitos_suman_exactamente_el_total():
    f = calcular_financiero({"Backend": 77.3, "Frontend": 31.9}, TARIFAS, margen_pct=27, contingencia_pct=13)
    assert sum(h["monto"] for h in f["hitos_pago"]) == f["total"]
    assert [h["porcentaje"] for h in f["hitos_pago"]] == [40, 30, 30]


def test_duracion_depende_del_rol_con_mas_horas():
    f = calcular_financiero({"Backend": 90, "Frontend": 10}, TARIFAS)
    assert f["duracion_semanas"] == 3  # 90 h / 30 h por semana


def test_tarifa_faltante():
    with pytest.raises(TarifaFaltante) as e:
        calcular_financiero({"Backend": 10, "QA": 5}, TARIFAS)
    assert e.value.roles == ["QA"]


def test_simular_endpoint(client, tarifas):
    r = client.post("/finanzas/simular", json={"horas_por_rol": {"Backend": 100, "Frontend": 50}})
    assert r.status_code == 200
    assert r.json()["total"] == 13_613_600


def test_simular_sin_tarifas_da_409(client):
    r = client.post("/finanzas/simular", json={"horas_por_rol": {"Backend": 10}})
    assert r.status_code == 409 and "Backend" in r.json()["detail"]


def test_simular_valida_parametros(client, tarifas):
    r = client.post("/finanzas/simular", json={"horas_por_rol": {"Backend": 10}, "descuento_pct": 90})
    assert r.status_code == 422
