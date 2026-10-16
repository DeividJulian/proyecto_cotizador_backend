from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from schemas.finanzas import SimulacionEntrada
from seguridad import usuario_actual
from services.finanzas import TarifaFaltante, calcular_financiero
from services.tarifas import tarifas_de

router = APIRouter(prefix="/finanzas", tags=["Finance"])


@router.post("/simular")
def simular(entrada: SimulacionEntrada, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Prices a set of hours per role using your rates (nothing is saved)."""
    tarifas = tarifas_de(db, usuario.id)
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
