from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from schemas.finance import SimulationInput
from security import current_user
from services.finance import MissingRate, calculate_financials
from services.rates import rates_of

router = APIRouter(prefix="/finance", tags=["Finanzas"])


@router.post("/simulate", summary="Simular precio")
def simulate(data: SimulationInput, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Calcula el precio de unas horas por rol con tus tarifas (no guarda nada)."""
    try:
        return calculate_financials(
            data.hours_by_role, rates_of(db, user.id), data.margin_pct, data.contingency_pct, data.discount_pct, data.vat_pct
        )
    except MissingRate as e:
        raise HTTPException(status_code=409, detail=str(e))
