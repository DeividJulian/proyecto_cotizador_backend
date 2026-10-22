"""Financial calculation of a quote: costs, contingency, margin, discount, VAT, schedule and payment milestones."""
import math

PRODUCTIVE_HOURS_PER_WEEK = 30  # real working hours per person per week

# (name shown to the user, percentage of the total, progress of the project when it is paid)
PAYMENT_MILESTONES = [
    ("Anticipo al firmar", 40, 0.0),
    ("Entrega de avance funcional", 30, 0.5),
    ("Entrega final y aceptación", 30, 1.0),
]


class MissingRate(Exception):
    def __init__(self, roles: list[str]):
        self.roles = roles
        super().__init__("Falta la tarifa de: " + ", ".join(roles))


def _pesos(value: float) -> int:
    return int(round(value))


def calculate_financials(
    hours_by_role: dict[str, float],
    rates: dict[str, int],
    margin_pct: float = 30.0,
    contingency_pct: float = 10.0,
    discount_pct: float = 0.0,
    vat_pct: float = 19.0,
) -> dict:
    """
    hours_by_role: role -> hours.  rates: role -> cost per hour (COP).
    Order: direct cost -> + contingency -> + margin -> - discount -> + VAT.
    """
    missing = sorted(r for r, h in hours_by_role.items() if h > 0 and r not in rates)
    if missing:
        raise MissingRate(missing)

    by_role = []
    for role, hours in sorted(hours_by_role.items()):
        if hours <= 0:
            continue
        by_role.append({"role": role, "hours": round(hours, 1), "hourly_rate": rates[role], "cost": _pesos(hours * rates[role])})

    direct_cost = sum(r["cost"] for r in by_role)
    contingency = _pesos(direct_cost * contingency_pct / 100)
    margin = _pesos((direct_cost + contingency) * margin_pct / 100)
    subtotal = direct_cost + contingency + margin
    discount = _pesos(subtotal * discount_pct / 100)
    taxable_base = subtotal - discount
    vat = _pesos(taxable_base * vat_pct / 100)
    total = taxable_base + vat

    max_hours = max((r["hours"] for r in by_role), default=0)
    weeks = max(1, math.ceil(max_hours / PRODUCTIVE_HOURS_PER_WEEK))

    milestones, paid = [], 0
    for i, (name, percentage, progress) in enumerate(PAYMENT_MILESTONES):
        amount = total - paid if i == len(PAYMENT_MILESTONES) - 1 else _pesos(total * percentage / 100)
        paid += amount
        milestones.append({"name": name, "percentage": percentage, "week": math.ceil(weeks * progress), "amount": amount})

    return {
        "by_role": by_role,
        "direct_cost": direct_cost,
        "contingency": contingency,
        "margin": margin,
        "subtotal": subtotal,
        "discount": discount,
        "taxable_base": taxable_base,
        "vat": vat,
        "total": total,
        "duration_weeks": weeks,
        "payment_milestones": milestones,
        "params": {
            "margin_pct": margin_pct,
            "contingency_pct": contingency_pct,
            "discount_pct": discount_pct,
            "vat_pct": vat_pct,
        },
    }
