from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from seguridad import usuario_actual
from services.finanzas import TarifaFaltante
from services.seed import borrar_cotizaciones, cargar_ejemplos, tiene_cotizaciones

router = APIRouter(tags=["Demo data"])


@router.post("/seed")
def cargar_seed(reiniciar: bool = False, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Loads example quotes into your account. With reiniciar=true it first deletes all your quotes."""
    if tiene_cotizaciones(db, usuario.id):
        if not reiniciar:
            raise HTTPException(
                status_code=409,
                detail="You already have quotes. Use /seed?reiniciar=true to delete them and load the examples.",
            )
        borrar_cotizaciones(db, usuario.id)
    try:
        resumen = cargar_ejemplos(db, usuario)
    except TarifaFaltante as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{e}. Restore the market rates in My rates.")
    return {"mensaje": "Example quotes loaded", "resumen": resumen}
