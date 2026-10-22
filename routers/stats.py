from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security import current_user
from services.stats import calculate_stats

router = APIRouter(tags=["Estadísticas"])


@router.get("/stats", summary="Mi tablero")
def stats(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Cotizaciones por estado, tasa de cierre, ticket promedio, horas y módulos más cotizados."""
    return calculate_stats(db, user.id)
