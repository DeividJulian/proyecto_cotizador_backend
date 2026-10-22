from collections import Counter

from sqlalchemy.orm import Session

from models.quote import Quote, QuoteItem
from services.catalog import CROSS_CUTTING
from services.quoting import STATUSES


def calculate_stats(db: Session, user_id: int) -> dict:
    """Personal dashboard: only the user's quotes count."""
    quotes = db.query(Quote).filter(Quote.user_id == user_id).all()
    by_status = {s: 0 for s in STATUSES}
    value = {s: 0 for s in STATUSES}
    hours_by_role: Counter = Counter()
    for q in quotes:
        by_status[q.status] = by_status.get(q.status, 0) + 1
        value[q.status] = value.get(q.status, 0) + q.total
        for role, row in (q.estimate or {}).get("by_role", {}).items():
            hours_by_role[role] += row["expected"]

    closed = by_status["accepted"] + by_status["rejected"]
    with_total = [q.total for q in quotes if q.total > 0]
    modules = Counter(
        name
        for (name,) in db.query(QuoteItem.name)
        .join(Quote, QuoteItem.quote_id == Quote.id)
        .filter(Quote.user_id == user_id, QuoteItem.category != CROSS_CUTTING)
    )
    return {
        "total_quotes": len(quotes),
        "by_status": by_status,
        "close_rate_pct": round(100 * by_status["accepted"] / closed, 1) if closed else None,
        "average_ticket": round(sum(with_total) / len(with_total)) if with_total else 0,
        "accepted_value": value["accepted"],
        "negotiating_value": value["sent"],
        "hours_by_role": {r: round(h, 1) for r, h in sorted(hours_by_role.items())},
        "top_modules": [{"module": m, "count": n} for m, n in modules.most_common(5)],
    }
