"""The four AI features. Our own code calculates everything (modules, PERT hours, price, milestones); the model
only reads those results and writes text. It never receives the client's name, emails, phones or account data.
"""
import json

from models.quote import Quote
from schemas.ai import (
    ClientQuestionsOutput,
    PriceExplanationOutput,
    ProposalWordingOutput,
    ScopeReviewOutput,
)
from services import llm
from services.catalog import COMPLEXITY_FACTORS, CROSS_CUTTING, MODULES
from services.privacy import Redactor
from services.proposal import WORDING_SECTIONS, numbers_in, pesos, section_title, split_sections

MAX_SUGGESTIONS = 5
MAX_ITEMS = 8

BASE_RULES = (
    "Eres un asesor que ayuda a freelancers de software en Colombia a cotizar proyectos. "
    "Responde siempre en español neutro, claro y breve. "
    "Los textos como [cliente], [empresa], [freelancer], [correo 1] o [teléfono 1] reemplazan datos personales: "
    "déjalos tal cual, sin inventar nombres."
)


def _redactor(quote: Quote) -> Redactor:
    return Redactor(
        {"[cliente]": quote.client_name, "[empresa]": quote.client_company, "[freelancer]": quote.user.name},
        emails=(quote.user.email,),
    )


def _as_json(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1)


def _clean(texts: list[str], redactor: Redactor, limit: int = MAX_ITEMS) -> list[str]:
    result = []
    for text in texts:
        text = redactor.restore(text).strip()
        if text and text not in result:
            result.append(text)
    return result[:limit]


def _modules(quote: Quote, redactor: Redactor) -> list[dict]:
    return [
        {
            "name": redactor.redact(i.name),
            "category": i.category,
            "complexity": i.complexity,
            "hours_optimistic": i.hours_optimistic,
            "hours_likely": i.hours_likely,
            "hours_pessimistic": i.hours_pessimistic,
            "hours_expected": i.hours_expected,
        }
        for i in quote.items
    ]


def _present_keys(quote: Quote) -> set[str]:
    """Catalog modules the quote already has: detected by the analysis or with the same name as an item."""
    keys = {m["key"] for m in (quote.analysis or {}).get("modules", [])}
    names = {i.name.strip().lower() for i in quote.items}
    keys |= {key for key, data in MODULES.items() if data["name"].lower() in names}
    return keys


# ---------- 1. Second opinion on the scope ----------

def review_scope(quote: Quote) -> dict:
    redactor = _redactor(quote)
    present = _present_keys(quote)
    catalog = [
        {"key": key, "name": data["name"], "examples": data["keywords"][:6]}
        for key, data in MODULES.items()
        if key not in present
    ]
    system = (
        f"{BASE_RULES} Revisas la descripción del alcance de un proyecto de software y das una segunda opinión: "
        "qué módulos del catálogo pide o necesita claramente la descripción y todavía no están en la cotización. "
        "Sugiere solo módulos del catálogo dado (usa su key exacta) y solo si la descripción los justifica; "
        "si no falta ninguno, devuelve la lista vacía. En reason explica en una frase qué parte del texto lo pide. "
        "En missing_details lista datos que faltan en la descripción para estimar mejor (máximo 5)."
    )
    user = _as_json({
        "title": redactor.redact(quote.title),
        "scope_description": redactor.redact(quote.scope_description),
        "modules_in_quote": [m["name"] for m in _modules(quote, redactor) if m["category"] != CROSS_CUTTING],
        "catalog": catalog,
    })
    output = llm.generate(system, user, ScopeReviewOutput)

    suggestions, seen = [], set()
    for s in output.suggestions:
        if s.key in present or s.key in seen:
            continue  # the model may repeat a module or suggest one that is already there
        seen.add(s.key)
        data = MODULES[s.key]
        suggestions.append({
            "key": s.key,
            "name": data["name"],
            "category": data["category"],
            "hours_likely": data["hours"] * COMPLEXITY_FACTORS["medium"],
            "split": dict(data["split"]),
            "reason": redactor.restore(s.reason).strip(),
        })
    return {
        "quote_id": quote.id,
        "suggestions": suggestions[:MAX_SUGGESTIONS],
        "missing_details": _clean(output.missing_details, redactor, 5),
    }


# ---------- 2. Price explanation ----------

def explain_price(quote: Quote) -> dict:
    redactor = _redactor(quote)
    fin = quote.financials
    system = (
        f"{BASE_RULES} Explicas a un freelancer, en lenguaje sencillo, de dónde sale el precio que ya calculó el "
        "sistema. Usa solo las cifras que recibes, escritas igual; no calcules cifras nuevas ni cambies ninguna. "
        "summary: 2 o 3 frases. drivers: lo que más pesa en el precio (máximo 5). "
        "ways_to_lower: cómo podría bajar el precio recortando o simplificando el alcance (máximo 4)."
    )
    user = _as_json({
        "title": redactor.redact(quote.title),
        "modules": _modules(quote, redactor),
        "hours_expected": quote.estimate.get("hours_expected"),
        "cost_by_role": [
            {"role": r["role"], "hours": r["hours"], "hourly_rate": pesos(r["hourly_rate"]), "cost": pesos(r["cost"])}
            for r in fin.get("by_role", [])
        ],
        "direct_cost": pesos(fin["direct_cost"]),
        "contingency": f"{quote.contingency_pct:g} % = {pesos(fin['contingency'])}",
        "margin": f"{quote.margin_pct:g} % = {pesos(fin['margin'])}",
        "discount": f"{quote.discount_pct:g} % = {pesos(fin['discount'])}",
        "vat": f"{quote.vat_pct:g} % = {pesos(fin['vat'])}",
        "total": pesos(fin["total"]),
        "duration_weeks": fin["duration_weeks"],
    })
    output = llm.generate(system, user, PriceExplanationOutput)
    return {
        "quote_id": quote.id,
        "summary": redactor.restore(output.summary).strip(),
        "drivers": _clean(output.drivers, redactor, 5),
        "ways_to_lower": _clean(output.ways_to_lower, redactor, 4),
    }


# ---------- 3. Questions and risks for the client ----------

def client_questions(quote: Quote) -> dict:
    redactor = _redactor(quote)
    system = (
        f"{BASE_RULES} Preparas la reunión de un freelancer con su cliente antes de enviar la cotización. "
        "questions: preguntas concretas para aclarar el alcance y evitar sorpresas (entre 4 y 8). "
        "risks: riesgos del proyecto que podrían aumentar las horas, cada uno con una forma de mitigarlo "
        "(máximo 5). Basate en la descripción y en los módulos; no hables de precios."
    )
    user = _as_json({
        "title": redactor.redact(quote.title),
        "scope_description": redactor.redact(quote.scope_description),
        "modules": [m["name"] for m in _modules(quote, redactor) if m["category"] != CROSS_CUTTING],
        "analysis_warnings": (quote.analysis or {}).get("warnings", []),
    })
    output = llm.generate(system, user, ClientQuestionsOutput)
    risks = []
    for r in output.risks[:5]:
        risk, mitigation = redactor.restore(r.risk).strip(), redactor.restore(r.mitigation).strip()
        if risk:
            risks.append({"risk": risk, "mitigation": mitigation})
    return {"quote_id": quote.id, "questions": _clean(output.questions, redactor), "risks": risks}


# ---------- 4. Proposal wording ----------

def improve_proposal(quote: Quote) -> dict:
    """Suggests a better wording for the text sections. Nothing is saved: the user applies what they like."""
    redactor = _redactor(quote)
    _, sections = split_sections(quote.proposal or "")
    editable = [(h, body.strip()) for h, body in sections if section_title(h) in WORDING_SECTIONS and body.strip()]
    system = (
        f"{BASE_RULES} Mejoras la redacción de secciones de una propuesta comercial para que suene profesional, "
        "clara y cercana. Reglas estrictas: no cambies, agregues ni quites cifras, montos, horas, semanas, "
        "porcentajes, fechas ni hitos (cada número debe quedar escrito exactamente igual); no prometas nada nuevo; "
        "conserva el formato Markdown (negritas, listas, citas). Devuelve cada sección con su mismo index."
    )
    user = _as_json([
        {"index": n, "title": section_title(h), "text": redactor.redact(text)} for n, (h, text) in enumerate(editable)
    ])
    output = llm.generate(system, user, ProposalWordingOutput)

    improved = {s.index: redactor.restore(s.text).strip() for s in output.sections if 0 <= s.index < len(editable)}
    changes, discarded = [], []
    for n, (heading, original) in enumerate(editable):
        text = improved.get(n)
        if not text or text == original:
            continue
        if numbers_in(text) != numbers_in(original):
            discarded.append(heading)  # the AI changed a figure: this suggestion is not shown
            continue
        changes.append({"heading": heading, "original": original, "improved": text})
    return {"quote_id": quote.id, "sections": changes, "discarded": discarded}
