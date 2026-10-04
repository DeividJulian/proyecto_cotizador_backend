"""Orquesta el análisis, la estimación y el cálculo financiero de una cotización."""
from sqlalchemy.orm import Session

from models.cotizacion import Cotizacion, ItemCotizacion
from models.tarifa import Tarifa
from services.alcance import analizar_alcance
from services.estimacion import construir_items, resumen_estimacion
from services.finanzas import calcular_financiero

TRANSICIONES = {
    "borrador": {"enviada"},
    "enviada": {"aceptada", "rechazada", "borrador"},
    "aceptada": set(),
    "rechazada": set(),
}


def tarifas_actuales(db: Session) -> dict[str, int]:
    return {t.rol: t.valor_hora for t in db.query(Tarifa).all()}


def recalcular(db: Session, cot: Cotizacion) -> None:
    """Recalcula estimación, financiero y total a partir de los ítems y los parámetros.

    Lanza TarifaFaltante si algún rol con horas no tiene tarifa (el router la convierte en 409).
    """
    if not cot.items:
        cot.estimacion, cot.financiero, cot.total = {}, {}, 0
        return
    confianza = (cot.analisis or {}).get("confianza", "media")
    estimacion = resumen_estimacion(cot.items, confianza)
    horas_rol = {rol: f["esperadas"] for rol, f in estimacion["por_rol"].items()}
    financiero = calcular_financiero(
        horas_rol, tarifas_actuales(db), cot.margen_pct, cot.contingencia_pct, cot.descuento_pct, cot.iva_pct
    )
    cot.estimacion, cot.financiero, cot.total = estimacion, financiero, financiero["total"]


def aplicar_analisis(cot: Cotizacion) -> dict:
    """Ejecuta la IA sobre el alcance: reemplaza los ítems de origen 'ia' y conserva los manuales."""
    analisis = analizar_alcance(cot.descripcion_alcance)
    if not analisis["modulos"]:
        return analisis
    cot.items[:] = [i for i in cot.items if i.origen == "manual"]
    for datos in construir_items(analisis["modulos"]):
        cot.items.append(ItemCotizacion(**datos))
    cot.analisis = analisis
    return analisis
