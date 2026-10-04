from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.tarifa import Tarifa
from schemas.finanzas import SimulacionEntrada
from services.finanzas import TarifaFaltante, calcular_financiero

router = APIRouter(prefix="/finanzas", tags=["Finance"])


@router.post("/simular")
def simular(entrada: SimulacionEntrada, db: Session = Depends(get_db)):
    """Prices a set of hours per role using the registered rates (nothing is saved)."""
    tarifas = {t.rol: t.valor_hora for t in db.query(Tarifa).all()}
    try:
        return calcular_financiero(
            entrada.horas_por_rol,
            tarifas,
            entrada.margen_pct,
            entrada.contingencia_pct,
            entrada.descuento_pct,
            entrada.iva_pct,
        )
    except TarifaFaltante as e:
        raise HTTPException(status_code=409, detail=str(e))
