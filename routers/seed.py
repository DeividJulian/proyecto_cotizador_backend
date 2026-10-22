from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security import current_user
from services.finance import MissingRate
from services.seed import delete_quotes, has_quotes, load_examples

router = APIRouter(tags=["Datos de ejemplo"])


@router.post("/seed", summary="Cargar ejemplos")
def seed(reset: bool = False, db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Carga cotizaciones de ejemplo en tu cuenta. Con reset=true primero borra todas tus cotizaciones."""
    if has_quotes(db, user.id):
        if not reset:
            raise HTTPException(
                status_code=409,
                detail="Ya tienes cotizaciones. Usa /seed?reset=true para borrarlas y cargar los ejemplos.",
            )
        delete_quotes(db, user.id)
    try:
        summary = load_examples(db, user)
    except MissingRate as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{e}. Restablece las tarifas de mercado en Mis tarifas.")
    return {"message": "Cotizaciones de ejemplo cargadas", "summary": summary}
