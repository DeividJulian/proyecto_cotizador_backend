from collections import Counter

from sqlalchemy.orm import Session

from models.cotizacion import Cotizacion, ItemCotizacion

ESTADOS = ["borrador", "enviada", "aceptada", "rechazada"]


def calcular_estadisticas(db: Session) -> dict:
    cotizaciones = db.query(Cotizacion).all()
    por_estado = {e: 0 for e in ESTADOS}
    valor = {e: 0 for e in ESTADOS}
    horas_rol: Counter = Counter()
    for c in cotizaciones:
        por_estado[c.estado] = por_estado.get(c.estado, 0) + 1
        valor[c.estado] = valor.get(c.estado, 0) + c.total
        for rol, fila in (c.estimacion or {}).get("por_rol", {}).items():
            horas_rol[rol] += fila["esperadas"]

    cerradas = por_estado["aceptada"] + por_estado["rechazada"]
    con_total = [c.total for c in cotizaciones if c.total > 0]
    modulos = Counter(
        nombre for (nombre,) in db.query(ItemCotizacion.nombre).filter(ItemCotizacion.categoria != "Cross-cutting")
    )
    return {
        "total_cotizaciones": len(cotizaciones),
        "por_estado": por_estado,
        "tasa_cierre_pct": round(100 * por_estado["aceptada"] / cerradas, 1) if cerradas else None,
        "ticket_promedio": round(sum(con_total) / len(con_total)) if con_total else 0,
        "valor_aceptado": valor["aceptada"],
        "valor_en_negociacion": valor["enviada"],
        "horas_por_rol": {r: round(h, 1) for r, h in sorted(horas_rol.items())},
        "modulos_mas_cotizados": [{"modulo": m, "veces": n} for m, n in modulos.most_common(5)],
    }
