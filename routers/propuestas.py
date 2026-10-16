from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from routers.cotizaciones import exigir_borrador, obtener_cotizacion
from seguridad import usuario_actual
from services.propuesta import generar_propuesta

router = APIRouter(prefix="/cotizaciones/{cotizacion_id}/propuesta", tags=["Commercial proposal"])


@router.post("")
def generar(cotizacion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Writes the commercial proposal in Markdown from the calculated data and saves it."""
    cot = obtener_cotizacion(db, cotizacion_id, usuario)
    exigir_borrador(cot)
    if not cot.items or not cot.financiero:
        raise HTTPException(status_code=409, detail="Analyze the quote before generating the proposal")
    cot.propuesta = generar_propuesta(cot)
    db.commit()
    return {"cotizacion_id": cot.id, "propuesta": cot.propuesta}


@router.get("")
def ver(cotizacion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    cot = obtener_cotizacion(db, cotizacion_id, usuario)
    if not cot.propuesta:
        raise HTTPException(status_code=404, detail="This quote has no proposal yet")
    return {"cotizacion_id": cot.id, "propuesta": cot.propuesta}


@router.get("/descargar", response_class=PlainTextResponse)
def descargar(cotizacion_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    cot = obtener_cotizacion(db, cotizacion_id, usuario)
    if not cot.propuesta:
        raise HTTPException(status_code=404, detail="This quote has no proposal yet")
    return PlainTextResponse(
        cot.propuesta,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="proposal-QT-{cot.id:04d}.md"'},
    )
