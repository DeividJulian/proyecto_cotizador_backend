from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from routers.quotes import get_quote, require_draft
from schemas.common import errors, json_errors
from schemas.proposal import ProposalOut, ProposalSectionsUpdate
from security import current_user
from services.proposal import build_proposal, numbers_in, quote_code, replace_sections, split_sections

router = APIRouter(prefix="/quotes/{quote_id}/proposal", tags=["Propuesta comercial"], responses=errors(401, 404, 409, 422))


@router.post("", response_model=ProposalOut, summary="Generar propuesta")
def generate(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Redacta la propuesta comercial en Markdown con los datos calculados y la guarda."""
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    if not quote.items or not quote.financials:
        raise HTTPException(status_code=409, detail="Analiza la cotización antes de generar la propuesta")
    quote.proposal = build_proposal(quote)
    db.commit()
    return {"quote_id": quote.id, "proposal": quote.proposal}


@router.patch("", response_model=ProposalOut, summary="Cambiar el texto de secciones")
def update_sections(
    quote_id: int, data: ProposalSectionsUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    """Reemplaza el texto de algunas secciones (por ejemplo, la redacción sugerida por la IA).

    Cada sección debe conservar exactamente las mismas cifras: montos, horas, semanas, fechas y porcentajes.
    """
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    if not quote.proposal:
        raise HTTPException(status_code=404, detail="Esta cotización aún no tiene propuesta")
    current = dict(split_sections(quote.proposal)[1])
    texts = {}
    for section in data.sections:
        if section.heading not in current:
            raise HTTPException(status_code=404, detail=f"La propuesta no tiene la sección «{section.heading}»")
        if numbers_in(section.text) != numbers_in(current[section.heading]):
            raise HTTPException(
                status_code=409,
                detail=f"El texto nuevo de «{section.heading}» cambia cifras de la propuesta: no se aplicó",
            )
        texts[section.heading] = section.text
    quote.proposal = replace_sections(quote.proposal, texts)
    db.commit()
    return {"quote_id": quote.id, "proposal": quote.proposal}


@router.get("", response_model=ProposalOut, summary="Ver propuesta")
def read(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    if not quote.proposal:
        raise HTTPException(status_code=404, detail="Esta cotización aún no tiene propuesta")
    return {"quote_id": quote.id, "proposal": quote.proposal}


@router.get(
    "/download",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/markdown": {}}}, **json_errors(401, 404, 409, 422)},
    summary="Descargar propuesta",
)
def download(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    if not quote.proposal:
        raise HTTPException(status_code=404, detail="Esta cotización aún no tiene propuesta")
    return PlainTextResponse(
        quote.proposal,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="propuesta-{quote_code(quote.id)}.md"'},
    )
