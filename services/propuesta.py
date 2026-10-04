"""Generación de la propuesta comercial en Markdown a partir de una cotización calculada."""
from datetime import datetime, timedelta, timezone

VIGENCIA_DIAS = 30

COMPLEJIDAD_TEXTO = {"baja": "low", "media": "medium", "alta": "high"}


def pesos(valor: int | float) -> str:
    """Formato de moneda: $13,613,600 COP."""
    return "$" + f"{int(round(valor)):,}" + " COP"


def _por_categoria(items) -> dict[str, list]:
    grupos: dict[str, list] = {}
    for item in items:
        grupos.setdefault(item.categoria, []).append(item)
    return grupos


def generar_propuesta(cot, fecha: datetime | None = None) -> str:
    fecha = fecha or datetime.now(timezone.utc)
    fin = fecha + timedelta(days=VIGENCIA_DIAS)
    fin_ = cot.financiero
    est = cot.estimacion
    cliente = cot.cliente
    desarrollo = [i for i in cot.items if i.categoria != "Cross-cutting"]
    transversales = [i for i in cot.items if i.categoria == "Cross-cutting"]

    L: list[str] = []
    L += [f"# Commercial proposal: {cot.titulo}", ""]
    L += [
        f"**Client:** {cliente.nombre}" + (f" ({cliente.empresa})" if cliente.empresa else ""),
        f"**Date:** {fecha:%d/%m/%Y}",
        f"**Valid until:** {fin:%d/%m/%Y} ({VIGENCIA_DIAS} days)",
        f"**Reference:** QT-{cot.id:04d}",
        "",
    ]

    L += ["## 1. Executive summary", ""]
    L += [
        f"We present the proposal for **{cot.titulo}**. The project includes {len(desarrollo)} functional "
        f"modules, with an estimated effort of **{est['horas_esperadas']:.0f} hours** and an approximate "
        f"duration of **{fin_['duracion_semanas']} weeks**. The total investment is "
        f"**{pesos(fin_['total'])}** (VAT included).",
        "",
    ]

    L += ["## 2. Scope", "", "> " + cot.descripcion_alcance.strip().replace("\n", "\n> "), ""]

    L += ["## 3. Deliverables", ""]
    for categoria, grupo in _por_categoria(desarrollo).items():
        L += [f"**{categoria}**", ""]
        for i in grupo:
            L.append(f"- {i.nombre} ({COMPLEJIDAD_TEXTO.get(i.complejidad, i.complejidad)} complexity)")
        L.append("")
    if transversales:
        L += ["**Included services**", ""]
        L += [f"- {i.nombre}" for i in transversales]
        L.append("")

    L += ["## 4. Schedule", ""]
    L += [f"Estimated duration: **{fin_['duracion_semanas']} weeks** from signing and down payment.", ""]
    L += ["| Milestone | Week |", "|---|---|"]
    L += [f"| {h['nombre']} | {h['semana']} |" for h in fin_["hitos_pago"]]
    L.append("")

    L += ["## 5. Investment", ""]
    L += ["| Item | Amount |", "|---|---:|"]
    L += [f"| Project development and services | {pesos(fin_['costo_directo'] + fin_['contingencia'] + fin_['margen'])} |"]
    if fin_["descuento"]:
        L += [f"| Discount ({fin_['parametros']['descuento_pct']:g}%) | -{pesos(fin_['descuento'])} |"]
    L += [
        f"| Subtotal | {pesos(fin_['base_gravable'])} |",
        f"| VAT ({fin_['parametros']['iva_pct']:g}%) | {pesos(fin_['iva'])} |",
        f"| **Total** | **{pesos(fin_['total'])}** |",
        "",
    ]

    L += ["## 6. Payment terms", ""]
    L += ["| Milestone | Percentage | Amount |", "|---|---:|---:|"]
    L += [f"| {h['nombre']} | {h['porcentaje']}% | {pesos(h['monto'])} |" for h in fin_["hitos_pago"]]
    L.append("")

    L += ["## 7. Assumptions and exclusions", ""]
    L += [
        "- The estimate is based on the scope description above; scope changes are quoted separately.",
        f"- A {fin_['parametros']['contingencia_pct']:g}% contingency is included for reasonable unforeseen events.",
        "- The client provides content, access and feedback within a maximum of 3 business days.",
        "- Does not include third-party license, domain or infrastructure costs.",
    ]
    if cot.analisis.get("confianza") == "baja":
        L.append("- The scope description is general: the estimate may change as requirements are detailed.")
    L.append("")

    L += ["## 8. Validity", "", f"This proposal is valid for {VIGENCIA_DIAS} calendar days, until {fin:%d/%m/%Y}.", ""]
    return "\n".join(L)
