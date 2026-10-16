from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from seguridad import usuario_actual
from services.estadisticas import calcular_estadisticas

router = APIRouter(tags=["Analytics"])


@router.get("/estadisticas")
def estadisticas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Your dashboard: quotes by status, close rate, average ticket, hours and most quoted modules."""
    return calcular_estadisticas(db, usuario.id)
