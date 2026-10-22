"""Effort estimate with the three-point method (PERT)."""
from services.catalog import (
    COMPLEXITY_FACTORS,
    CROSS_CUTTING,
    CROSS_CUTTING_WORK,
    DEFAULT_SPLIT,
    MODULES,
    PERT_RANGE,
    ROLES,
)

HOUR_FIELDS = ("hours_optimistic", "hours_likely", "hours_pessimistic")


def pert(optimistic: float, likely: float, pessimistic: float) -> float:
    """PERT expected value: (O + 4M + P) / 6."""
    return (optimistic + 4 * likely + pessimistic) / 6


def _hours(likely: float, complexity: str) -> dict:
    factor_o, factor_p = PERT_RANGE[complexity]
    optimistic, pessimistic = likely * factor_o, likely * factor_p
    return {
        "hours_optimistic": round(optimistic, 1),
        "hours_likely": round(likely, 1),
        "hours_pessimistic": round(pessimistic, 1),
        "hours_expected": round(pert(optimistic, likely, pessimistic), 1),
    }


def item_from_module(module: dict) -> dict:
    """Turns a module detected by the scope analysis into a quote line."""
    data = MODULES[module["key"]]
    likely = data["hours"] * COMPLEXITY_FACTORS[module["complexity"]]
    return {
        "name": module["name"],
        "category": module["category"],
        "complexity": module["complexity"],
        "source": "ai",
        "split": dict(data["split"]),
        "reasons": module["reasons"],
        **_hours(likely, module["complexity"]),
    }


def manual_item(name: str, category: str, complexity: str, hours_likely: float, split: dict | None) -> dict:
    return {
        "name": name,
        "category": category,
        "complexity": complexity,
        "source": "manual",
        "split": split or dict(DEFAULT_SPLIT),
        "reasons": "Agregado manualmente",
        **_hours(hours_likely, complexity),
    }


def cross_cutting_items(development_items: list[dict]) -> list[dict]:
    """QA, management and deployment are calculated as a percentage of the development work."""
    result = []
    for work in CROSS_CUTTING_WORK:
        total = {k: sum(i[k] for i in development_items) for k in HOUR_FIELDS}
        o, m, p = (max(work["minimum"] * factor, total[k] * work["share"]) for k, factor in
                   (("hours_optimistic", 0.8), ("hours_likely", 1.0), ("hours_pessimistic", 1.5)))
        result.append(
            {
                "name": work["name"],
                "category": CROSS_CUTTING,
                "complexity": "medium",
                "source": "ai",
                "split": {work["role"]: 1.0},
                "reasons": f"{round(work['share'] * 100)} % de las horas de desarrollo (mínimo {work['minimum']} h)",
                "hours_optimistic": round(o, 1),
                "hours_likely": round(m, 1),
                "hours_pessimistic": round(p, 1),
                "hours_expected": round(pert(o, m, p), 1),
            }
        )
    return result


def build_items(modules: list[dict]) -> list[dict]:
    development = [item_from_module(m) for m in modules]
    return development + cross_cutting_items(development)


def _empty_row() -> dict:
    return {"optimistic": 0.0, "likely": 0.0, "pessimistic": 0.0, "expected": 0.0}


def hours_by_role(items: list) -> dict:
    """Adds up the hours of every line split by role, in the three scenarios and the expected one."""
    totals = {role: _empty_row() for role in ROLES}
    for item in items:
        get = item.get if isinstance(item, dict) else lambda k, i=item: getattr(i, k)
        for role, fraction in (get("split") or {}).items():
            row = totals.setdefault(role, _empty_row())
            row["optimistic"] += get("hours_optimistic") * fraction
            row["likely"] += get("hours_likely") * fraction
            row["pessimistic"] += get("hours_pessimistic") * fraction
            row["expected"] += get("hours_expected") * fraction
    return {role: {k: round(v, 1) for k, v in row.items()} for role, row in totals.items() if row["likely"] > 0}


def summarize_estimate(items: list, confidence: str = "medium") -> dict:
    by_role = hours_by_role(items)
    total = lambda key: round(sum(r[key] for r in by_role.values()), 1)  # noqa: E731
    return {
        "by_role": by_role,
        "hours_optimistic": total("optimistic"),
        "hours_likely": total("likely"),
        "hours_pessimistic": total("pessimistic"),
        "hours_expected": total("expected"),
        "confidence": confidence,
    }
