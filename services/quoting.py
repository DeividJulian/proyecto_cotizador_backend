"""Runs the analysis, the estimate and the financial calculation of a quote."""
from sqlalchemy.orm import Session

from models.quote import Quote, QuoteItem
from services.estimation import build_items, summarize_estimate
from services.finance import calculate_financials
from services.rates import rates_of
from services.scope import analyze_scope

STATUSES = ["draft", "sent", "accepted", "rejected"]

TRANSITIONS = {
    "draft": {"sent"},
    "sent": {"accepted", "rejected", "draft"},
    "accepted": set(),
    "rejected": set(),
}


def recalculate(db: Session, quote: Quote) -> None:
    """Recalculates the estimate, the financials and the total from the items, the parameters and the owner's rates.

    Raises MissingRate when a role with hours has no rate (the router turns it into a 409).
    """
    if not quote.items:
        quote.estimate, quote.financials, quote.total = {}, {}, 0
        return
    confidence = (quote.analysis or {}).get("confidence", "medium")
    estimate = summarize_estimate(quote.items, confidence)
    hours = {role: row["expected"] for role, row in estimate["by_role"].items()}
    financials = calculate_financials(
        hours, rates_of(db, quote.user_id), quote.margin_pct, quote.contingency_pct, quote.discount_pct, quote.vat_pct
    )
    quote.estimate, quote.financials, quote.total = estimate, financials, financials["total"]


def apply_analysis(quote: Quote) -> dict:
    """Analyzes the scope: replaces the items that came from the analysis and keeps the manual ones."""
    analysis = analyze_scope(quote.scope_description)
    if not analysis["modules"]:
        return analysis
    quote.items[:] = [i for i in quote.items if i.source == "manual"]
    for data in build_items(analysis["modules"]):
        quote.items.append(QuoteItem(**data))
    quote.analysis = analysis
    return analysis
