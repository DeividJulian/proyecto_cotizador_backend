import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.quote import Quote
from models.user import User
from schemas.common import Message, errors
from schemas.quote import QuoteCard, QuoteCreate, QuoteOut, QuoteSummary, QuoteUpdate, SimilarQuote, StatusChange
from security import current_user
from services.catalog import CROSS_CUTTING
from services.finance import MissingRate
from services.quoting import TRANSITIONS, apply_analysis, recalculate
from services.similarity import cosine_similarity

logger = logging.getLogger("cotizador.api")
router = APIRouter(prefix="/quotes", tags=["Cotizaciones"], responses=errors(401, 404, 409, 422))

STATUS_LABELS = {"draft": "borrador", "sent": "enviada", "accepted": "aceptada", "rejected": "rechazada"}


def get_quote(db: Session, quote_id: int, user: User) -> Quote:
    """Only the owner can see or change a quote; for any other user it does not exist (404)."""
    quote = db.query(Quote).filter(Quote.id == quote_id, Quote.user_id == user.id).first()
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    return quote


def require_draft(quote: Quote) -> None:
    if quote.status != "draft":
        raise HTTPException(
            status_code=409,
            detail=f"La cotización está {STATUS_LABELS.get(quote.status, quote.status)}: solo se edita en borrador",
        )


def save_recalculated(db: Session, quote: Quote) -> Quote:
    """Recalculates and saves; when a rate is missing everything is undone and the answer is 409."""
    try:
        recalculate(db, quote)
    except MissingRate as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{e}. Agrégala en Mis tarifas.")
    db.commit()
    db.refresh(quote)
    return quote


def summary_of(quote: Quote) -> dict:
    est, fin = quote.estimate or {}, quote.financials or {}
    return {
        "id": quote.id,
        "title": quote.title,
        "client": quote.client_name,
        "status": quote.status,
        "modules": sum(1 for i in quote.items if i.category != CROSS_CUTTING),
        "hours_expected": est.get("hours_expected", 0),
        "hours_range": [est.get("hours_optimistic", 0), est.get("hours_pessimistic", 0)],
        "confidence": est.get("confidence"),
        "duration_weeks": fin.get("duration_weeks", 0),
        "total": quote.total,
        "has_proposal": bool(quote.proposal),
    }


@router.post("", response_model=QuoteOut, status_code=201, summary="Crear cotización")
def create_quote(data: QuoteCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = Quote(user_id=user.id, **data.model_dump())
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("", response_model=list[QuoteSummary], summary="Mis cotizaciones")
def list_quotes(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(current_user)):
    query = db.query(Quote).filter(Quote.user_id == user.id)
    if status:
        query = query.filter(Quote.status == status)
    return query.order_by(Quote.id.desc()).all()


@router.get("/{quote_id}", response_model=QuoteOut, summary="Ver cotización")
def read_quote(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return get_quote(db, quote_id, user)


@router.put("/{quote_id}", response_model=QuoteOut, summary="Editar cotización")
def update_quote(quote_id: int, data: QuoteUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is None:
            continue
        if field.startswith("client_"):
            value = value or None  # an empty string clears the optional field
        setattr(quote, field, value)
    return save_recalculated(db, quote)


@router.delete("/{quote_id}", response_model=Message, summary="Eliminar cotización")
def delete_quote(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    db.delete(quote)
    db.commit()
    return {"message": "Cotización eliminada"}


@router.post("/{quote_id}/analyze", response_model=QuoteOut, summary="Analizar el alcance")
def analyze_quote(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Detecta los módulos, estima las horas con PERT y calcula el precio."""
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    analysis = apply_analysis(quote)
    if not analysis["modules"]:
        raise HTTPException(status_code=422, detail=" ".join(analysis["warnings"]))
    logger.info("Quote %s analyzed: %s modules", quote.id, len(analysis["modules"]))
    return save_recalculated(db, quote)


@router.get("/{quote_id}/summary", response_model=QuoteCard, summary="Resumen de la cotización")
def quote_summary(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Vista compacta para tarjetas: total, horas, duración y confianza."""
    return summary_of(get_quote(db, quote_id, user))


@router.post("/{quote_id}/status", response_model=QuoteOut, summary="Cambiar estado")
def change_status(quote_id: int, data: StatusChange, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Seguimiento de la propuesta: borrador → enviada al cliente → aceptada o rechazada."""
    quote = get_quote(db, quote_id, user)
    if data.status not in TRANSITIONS[quote.status]:
        allowed = ", ".join(STATUS_LABELS[s] for s in sorted(TRANSITIONS[quote.status])) or "ninguno (estado final)"
        raise HTTPException(
            status_code=409,
            detail=f"No se puede pasar de {STATUS_LABELS[quote.status]} a {STATUS_LABELS[data.status]}. Permitidos: {allowed}",
        )
    if data.status == "sent" and not quote.proposal:
        raise HTTPException(status_code=409, detail="Genera la propuesta antes de enviar la cotización")
    quote.status = data.status
    db.commit()
    db.refresh(quote)
    logger.info("Quote %s -> %s", quote.id, quote.status)
    return quote


@router.get("/{quote_id}/similar", response_model=list[SimilarQuote], summary="Cotizaciones parecidas")
def similar_quotes(
    quote_id: int,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    """Tus cotizaciones anteriores con un alcance parecido (TF-IDF y coseno): sirven de referencia de precio."""
    quote = get_quote(db, quote_id, user)
    others = db.query(Quote).filter(Quote.user_id == user.id, Quote.id != quote.id).all()
    corpus = [o.scope_description for o in others]
    scored = [
        {
            "id": o.id,
            "title": o.title,
            "status": o.status,
            "total": o.total,
            "similarity": cosine_similarity(quote.scope_description, o.scope_description, corpus),
        }
        for o in others
    ]
    scored = [s for s in scored if s["similarity"] > 0]
    return sorted(scored, key=lambda s: s["similarity"], reverse=True)[:limit]
