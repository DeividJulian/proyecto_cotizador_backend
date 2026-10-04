from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from services.estadisticas import calcular_estadisticas

router = APIRouter(tags=["Analytics"])


@router.get("/estadisticas")
def estadisticas(db: Session = Depends(get_db)):
    """Sales dashboard: quotes by status, close rate, average ticket, hours and most requested modules."""
    return calcular_estadisticas(db)
