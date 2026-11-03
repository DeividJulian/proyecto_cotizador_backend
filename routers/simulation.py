from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from routers.quotes import get_quote
from schemas.common import errors
from schemas.simulation import SimulationRequest, SimulationResult
from security import current_user
from services import simulation

router = APIRouter(prefix="/quotes/{quote_id}/simulation", tags=["Simulación (Monte Carlo)"], responses=errors(401, 404, 409, 422))


@router.post("", response_model=SimulationResult, summary="Simular el riesgo")
def simulate_quote(
    quote_id: int, data: SimulationRequest, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    """Simula miles de proyectos posibles con las horas PERT de la cotización (no guarda nada).

    Respaldo en REST (JSON) del servicio gRPC cotizador.v1.SimulationService/Simulate, que además envía el progreso.
    """
    quote = get_quote(db, quote_id, user)
    try:
        return simulation.run(quote, data.runs, data.samples)
    except simulation.SimulationUnavailable as e:
        raise HTTPException(status_code=409, detail=str(e))
    except simulation.InvalidSimulation as e:
        raise HTTPException(status_code=422, detail=str(e))
