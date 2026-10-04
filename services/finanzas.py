"""Cálculo financiero de una cotización: costos, contingencia, margen, descuento, IVA, cronograma e hitos de pago."""
import math

HORAS_PRODUCTIVAS_SEMANA = 30  # horas reales de trabajo por persona y semana

HITOS_PAGO = [
    ("Down payment on signing", 40, 0.0),
    ("Functional progress delivery", 30, 0.5),
    ("Final delivery and acceptance", 30, 1.0),
]


class TarifaFaltante(Exception):
    def __init__(self, roles: list[str]):
        self.roles = roles
        super().__init__("Missing rate for: " + ", ".join(roles))


def _pesos(valor: float) -> int:
    return int(round(valor))


def calcular_financiero(
    horas_rol: dict[str, float],
    tarifas: dict[str, int],
    margen_pct: float = 30.0,
    contingencia_pct: float = 10.0,
    descuento_pct: float = 0.0,
    iva_pct: float = 19.0,
) -> dict:
    """
    horas_rol: rol -> horas.  tarifas: rol -> costo por hora (COP).
    Orden: costo directo -> + contingencia -> + margen -> - descuento -> + IVA.
    """
    faltantes = sorted(r for r, h in horas_rol.items() if h > 0 and r not in tarifas)
    if faltantes:
        raise TarifaFaltante(faltantes)

    detalle = []
    for rol, horas in sorted(horas_rol.items()):
        if horas <= 0:
            continue
        detalle.append({"rol": rol, "horas": round(horas, 1), "valor_hora": tarifas[rol], "costo": _pesos(horas * tarifas[rol])})

    costo_directo = sum(d["costo"] for d in detalle)
    contingencia = _pesos(costo_directo * contingencia_pct / 100)
    margen = _pesos((costo_directo + contingencia) * margen_pct / 100)
    subtotal = costo_directo + contingencia + margen
    descuento = _pesos(subtotal * descuento_pct / 100)
    base_gravable = subtotal - descuento
    iva = _pesos(base_gravable * iva_pct / 100)
    total = base_gravable + iva

    max_horas = max((d["horas"] for d in detalle), default=0)
    semanas = max(1, math.ceil(max_horas / HORAS_PRODUCTIVAS_SEMANA))

    hitos, acumulado = [], 0
    for i, (nombre, porcentaje, avance) in enumerate(HITOS_PAGO):
        monto = total - acumulado if i == len(HITOS_PAGO) - 1 else _pesos(total * porcentaje / 100)
        acumulado += monto
        hitos.append({"nombre": nombre, "porcentaje": porcentaje, "semana": math.ceil(semanas * avance), "monto": monto})

    return {
        "detalle_por_rol": detalle,
        "costo_directo": costo_directo,
        "contingencia": contingencia,
        "margen": margen,
        "subtotal": subtotal,
        "descuento": descuento,
        "base_gravable": base_gravable,
        "iva": iva,
        "total": total,
        "duracion_semanas": semanas,
        "hitos_pago": hitos,
        "parametros": {
            "margen_pct": margen_pct,
            "contingencia_pct": contingencia_pct,
            "descuento_pct": descuento_pct,
            "iva_pct": iva_pct,
        },
    }
