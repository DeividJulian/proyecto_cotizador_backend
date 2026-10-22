from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from routers.quotes import get_quote, require_draft
from security import current_user
from services.proposal import build_proposal, quote_code

router = APIRouter(prefix="/quotes/{quote_id}/proposal", tags=["Propuesta comercial"])


@router.post("", summary="Generar propuesta")
def generate(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Redacta la propuesta comercial en Markdown con los datos calculados y la guarda."""
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    if not quote.items or not quote.financials:
        raise HTTPException(status_code=409, detail="Analiza la cotización antes de generar la propuesta")
    quote.proposal = build_proposal(quote)
    db.commit()
    return {"quote_id": quote.id, "proposal": quote.proposal}


@router.get("", summary="Ver propuesta")
def read(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    if not quote.proposal:
        raise HTTPException(status_code=404, detail="Esta cotización aún no tiene propuesta")
    return {"quote_id": quote.id, "proposal": quote.proposal}


@router.get("/download", response_class=PlainTextResponse, summary="Descargar propuesta")
def download(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    if not quote.proposal:
        raise HTTPException(status_code=404, detail="Esta cotización aún no tiene propuesta")
    return PlainTextResponse(
        quote.proposal,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="propuesta-{quote_code(quote.id)}.md"'},
    )
