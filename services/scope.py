"""Scope analysis: detects modules, complexity and confidence from the project description."""
import re
from functools import lru_cache

from services.catalog import HIGH_SIGNALS, LOW_SIGNALS, MODULES
from services.nlp import normalize


@lru_cache(maxsize=None)
def _pattern(keyword: str) -> re.Pattern:
    return re.compile(r"(?<![a-z0-9])" + re.escape(normalize(keyword)) + r"(?![a-z0-9])")


_PATTERNS = {key: [(k, _pattern(k)) for k in data["keywords"]] for key, data in MODULES.items()}


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"[.;\n!?]+", normalize(text)) if s.strip()]


def _signals(normal_text: str, signals: list[str]) -> list[str]:
    return sorted({s for s in signals if _pattern(s).search(normal_text)})


def analyze_scope(text: str) -> dict:
    normal = normalize(text)
    sentences = _sentences(text)
    global_high = _signals(normal, HIGH_SIGNALS)
    global_low = _signals(normal, LOW_SIGNALS)

    modules = []
    for key, patterns in _PATTERNS.items():
        matched = [keyword for keyword, pattern in patterns if pattern.search(normal)]
        if not matched:
            continue

        module_sentences = [s for s in sentences if any(p.search(s) for _, p in patterns)]
        reasons = []
        if any(_signals(s, HIGH_SIGNALS) for s in module_sentences):
            complexity = "high"
            reasons.append("la descripción lo califica como complejo o de gran escala")
        elif any(_signals(s, LOW_SIGNALS) for s in module_sentences):
            complexity = "low"
            reasons.append("la descripción lo califica como sencillo o básico")
        elif len(module_sentences) >= 3:
            complexity = "high"
            reasons.append("se menciona en varias partes del alcance")
        elif len(global_high) >= 2:
            complexity = "high"
            reasons.append("el proyecto en general se describe como complejo")
        elif global_low:
            complexity = "low"
            reasons.append("el proyecto en general se describe como sencillo o un prototipo")
        else:
            complexity = "medium"
            reasons.append("sin indicios de complejidad especial")

        modules.append(
            {
                "key": key,
                "name": MODULES[key]["name"],
                "category": MODULES[key]["category"],
                "complexity": complexity,
                "matched_keywords": matched,
                "reasons": "; ".join(reasons),
            }
        )

    n = len(modules)
    length = len(text.strip())
    warnings = []
    if length < 120:
        warnings.append("El alcance es muy corto: describe más funcionalidades para una estimación confiable.")
    if n == 0:
        warnings.append("No se detectó ningún módulo conocido (login, pagos, reportes, app móvil, etc.).")

    if n >= 4 and length >= 300:
        confidence = "high"
    elif n >= 2 and length >= 120:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "modules": modules,
        "high_complexity_signals": global_high,
        "low_complexity_signals": global_low,
        "confidence": confidence,
        "warnings": warnings,
    }
