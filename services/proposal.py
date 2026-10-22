"""Commercial proposal in Markdown, built from a calculated quote. The document is shown to the client: Spanish."""
import re
from collections import Counter
from datetime import datetime, timedelta, timezone

from services.catalog import CROSS_CUTTING

VALIDITY_DAYS = 30

# Sections whose wording the AI may improve: the others are tables and lists built from the numbers
WORDING_SECTIONS = ("Resumen ejecutivo", "Alcance", "Supuestos y exclusiones")

_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

COMPLEXITY_LABELS = {"low": "baja", "medium": "media", "high": "alta"}


def pesos(value: int | float) -> str:
    """Colombian format: $13.613.600 COP."""
    return "$" + f"{int(round(value)):,}".replace(",", ".") + " COP"


def quote_code(quote_id: int) -> str:
    return f"COT-{quote_id:04d}"


def _by_category(items) -> dict[str, list]:
    groups: dict[str, list] = {}
    for item in items:
        groups.setdefault(item.category, []).append(item)
    return groups


def build_proposal(quote, date: datetime | None = None) -> str:
    date = date or datetime.now(timezone.utc)
    valid_until = date + timedelta(days=VALIDITY_DAYS)
    fin = quote.financials
    est = quote.estimate
    development = [i for i in quote.items if i.category != CROSS_CUTTING]
    cross_cutting = [i for i in quote.items if i.category == CROSS_CUTTING]
    client = " · ".join(p for p in (quote.client_name, quote.client_company) if p)

    lines: list[str] = []
    lines += [f"# Propuesta comercial: {quote.title}", ""]
    if client:
        lines.append(f"**Cliente:** {client}")
    lines += [
        f"**Preparada por:** {quote.user.name}",
        f"**Fecha:** {date:%d/%m/%Y}",
        f"**Vigencia:** hasta el {valid_until:%d/%m/%Y} ({VALIDITY_DAYS} días)",
        f"**Referencia:** {quote_code(quote.id)}",
        "",
    ]

    lines += ["## 1. Resumen ejecutivo", ""]
    lines += [
        f"Presentamos la propuesta para **{quote.title}**. El proyecto comprende {len(development)} módulos "
        f"funcionales, con un esfuerzo estimado de **{est['hours_expected']:.0f} horas** y una duración "
        f"aproximada de **{fin['duration_weeks']} semanas**. La inversión total es de "
        f"**{pesos(fin['total'])}** (IVA incluido).",
        "",
    ]

    lines += ["## 2. Alcance", "", "> " + quote.scope_description.strip().replace("\n", "\n> "), ""]

    lines += ["## 3. Entregables", ""]
    for category, group in _by_category(development).items():
        lines += [f"**{category}**", ""]
        for item in group:
            lines.append(f"- {item.name} (complejidad {COMPLEXITY_LABELS.get(item.complexity, item.complexity)})")
        lines.append("")
    if cross_cutting:
        lines += ["**Servicios incluidos**", ""]
        lines += [f"- {i.name}" for i in cross_cutting]
        lines.append("")

    lines += ["## 4. Cronograma", ""]
    lines += [f"Duración estimada: **{fin['duration_weeks']} semanas** desde la firma y el anticipo.", ""]
    lines += ["| Hito | Semana |", "|---|---|"]
    lines += [f"| {m['name']} | {m['week']} |" for m in fin["payment_milestones"]]
    lines.append("")

    lines += ["## 5. Inversión", ""]
    lines += ["| Concepto | Valor |", "|---|---:|"]
    lines += [f"| Desarrollo y servicios del proyecto | {pesos(fin['direct_cost'] + fin['contingency'] + fin['margin'])} |"]
    if fin["discount"]:
        lines += [f"| Descuento ({fin['params']['discount_pct']:g} %) | -{pesos(fin['discount'])} |"]
    lines += [
        f"| Subtotal | {pesos(fin['taxable_base'])} |",
        f"| IVA ({fin['params']['vat_pct']:g} %) | {pesos(fin['vat'])} |",
        f"| **Total** | **{pesos(fin['total'])}** |",
        "",
    ]

    lines += ["## 6. Condiciones de pago", ""]
    lines += ["| Hito | Porcentaje | Monto |", "|---|---:|---:|"]
    lines += [f"| {m['name']} | {m['percentage']} % | {pesos(m['amount'])} |" for m in fin["payment_milestones"]]
    lines.append("")

    lines += ["## 7. Supuestos y exclusiones", ""]
    lines += [
        "- La estimación parte de la descripción del alcance anterior; los cambios de alcance se cotizan por separado.",
        f"- Se incluye una contingencia del {fin['params']['contingency_pct']:g} % para imprevistos razonables.",
        "- El cliente entrega contenidos, accesos y retroalimentación en un plazo máximo de 3 días hábiles.",
        "- No incluye costos de licencias, dominios ni infraestructura de terceros.",
    ]
    if (quote.analysis or {}).get("confidence") == "low":
        lines.append("- La descripción del alcance es general: la estimación puede variar al detallar los requisitos.")
    lines.append("")

    lines += [
        "## 8. Vigencia",
        "",
        f"Esta propuesta es válida por {VALIDITY_DAYS} días calendario, hasta el {valid_until:%d/%m/%Y}.",
        "",
    ]
    return "\n".join(lines)


def split_sections(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    """("text before the first ## heading", [(heading, body), ...]). The body keeps its blank lines."""
    parts = _HEADING.split(markdown)
    return parts[0], list(zip(parts[1::2], parts[2::2]))


def section_title(heading: str) -> str:
    """'1. Resumen ejecutivo' -> 'Resumen ejecutivo'."""
    return re.sub(r"^\d+\.\s*", "", heading).strip()


def numbers_in(text: str) -> Counter:
    """Every figure of a text (amounts, hours, weeks, dates, percentages), to check that a rewrite kept them."""
    return Counter(_NUMBER.findall(text))


def replace_sections(markdown: str, texts: dict[str, str]) -> str:
    """Replaces the body of the sections named in `texts` (by full heading). The rest stays byte for byte."""
    preamble, sections = split_sections(markdown)
    rebuilt = [preamble]
    for heading, body in sections:
        if heading in texts:
            body = "\n\n" + texts[heading].strip() + "\n\n"
        rebuilt.append(f"## {heading}{body}")
    return "".join(rebuilt)
