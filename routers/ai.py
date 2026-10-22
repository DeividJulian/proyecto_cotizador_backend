from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from routers.quotes import get_quote
from schemas.ai import AIStatus, ClientQuestions, PriceExplanation, ProposalWording, ScopeReview
from security import current_user
from services import ai, llm

router = APIRouter(prefix="/ai", tags=["IA"])


def _run(function, *args):
    """Turns model errors into clear HTTP responses (never a 500)."""
    try:
        return function(*args)
    except llm.LLMNotConfigured as e:
        raise HTTPException(status_code=503, detail=f"La IA no está configurada: {e}")
    except llm.LLMRateLimited as e:
        headers = {"Retry-After": e.retry_after} if e.retry_after else None
        raise HTTPException(status_code=429, detail=str(e), headers=headers)
    except llm.LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/status", response_model=AIStatus, summary="Estado de la IA")
def ai_status(user: User = Depends(current_user)):
    """Indica si la IA está configurada, con qué proveedor y qué modelo usa."""
    return AIStatus(configured=llm.is_configured(), provider=llm.provider_name(), model=llm.model_name())


@router.post("/quotes/{quote_id}/scope-review", response_model=ScopeReview, summary="Segunda opinión del alcance")
def scope_review(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Módulos del catálogo que la descripción pide y el análisis no detectó, y datos que faltan. No cambia nada."""
    return _run(ai.review_scope, get_quote(db, quote_id, user))


@router.post("/quotes/{quote_id}/explain-price", response_model=PriceExplanation, summary="Explicar el precio")
def explain_price(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Explica en palabras sencillas el precio que calculó el sistema y cómo podría bajar. No cambia ninguna cifra."""
    quote = get_quote(db, quote_id, user)
    if not quote.items or not quote.total:
        raise HTTPException(status_code=409, detail="Analiza la cotización antes de pedir la explicación del precio")
    return _run(ai.explain_price, quote)


@router.post("/quotes/{quote_id}/client-questions", response_model=ClientQuestions, summary="Preguntas y riesgos")
def client_questions(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Preguntas para hacerle al cliente y riesgos que podrían aumentar las horas."""
    return _run(ai.client_questions, get_quote(db, quote_id, user))


@router.post("/quotes/{quote_id}/improve-proposal", response_model=ProposalWording, summary="Mejorar la redacción")
def improve_proposal(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Propone una mejor redacción de las secciones de texto, con las mismas cifras. No guarda nada."""
    quote = get_quote(db, quote_id, user)
    if not quote.proposal:
        raise HTTPException(status_code=409, detail="Genera la propuesta antes de mejorar su redacción")
    return _run(ai.improve_proposal, quote)
