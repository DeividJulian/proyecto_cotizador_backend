from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.rate import Rate
from models.user import User
from schemas.common import Message, errors
from schemas.rate import MarketRate, RateCreate, RateOut
from security import current_user
from services.rates import MARKET_RATES, reset_rates

router = APIRouter(prefix="/rates", tags=["Tarifas"], responses=errors(401, 404, 409, 422))


def role_in_use(db: Session, user_id: int, role: str, exclude_id: int | None = None) -> bool:
    query = db.query(Rate).filter(Rate.user_id == user_id, func.lower(Rate.role) == role.lower())
    if exclude_id is not None:
        query = query.filter(Rate.id != exclude_id)
    return query.first() is not None


def get_rate(db: Session, rate_id: int, user: User) -> Rate:
    rate = db.query(Rate).filter(Rate.id == rate_id, Rate.user_id == user.id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Tarifa no encontrada")
    return rate


def _list(db: Session, user: User) -> list[Rate]:
    return db.query(Rate).filter(Rate.user_id == user.id).order_by(Rate.id).all()


@router.get("", response_model=list[RateOut], summary="Mis tarifas")
def list_rates(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return _list(db, user)


@router.get("/market", response_model=list[MarketRate], summary="Tarifas de referencia del mercado")
def market_rates():
    """Valor por hora (COP) de cada rol con el que arranca toda cuenta nueva."""
    return [{"role": role, "hourly_rate": value} for role, value in MARKET_RATES.items()]


@router.post("", response_model=RateOut, status_code=201, summary="Crear tarifa")
def create_rate(data: RateCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    if role_in_use(db, user.id, data.role):
        raise HTTPException(status_code=409, detail="Ya tienes una tarifa para ese rol")
    rate = Rate(user_id=user.id, role=data.role, hourly_rate=data.hourly_rate)
    db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate


@router.post("/reset", response_model=list[RateOut], summary="Restablecer tarifas de mercado")
def reset_to_market(db: Session = Depends(get_db), user: User = Depends(current_user)):
    """Reemplaza tus tarifas por las de referencia del mercado."""
    reset_rates(db, user)
    db.commit()
    return _list(db, user)


@router.put("/{rate_id}", response_model=RateOut, summary="Editar tarifa")
def update_rate(rate_id: int, data: RateCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rate = get_rate(db, rate_id, user)
    if role_in_use(db, user.id, data.role, exclude_id=rate_id):
        raise HTTPException(status_code=409, detail="Ya tienes otra tarifa para ese rol")
    rate.role = data.role
    rate.hourly_rate = data.hourly_rate
    db.commit()
    db.refresh(rate)
    return rate


@router.delete("/{rate_id}", response_model=Message, summary="Eliminar tarifa")
def delete_rate(rate_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    rate = get_rate(db, rate_id, user)
    db.delete(rate)
    db.commit()
    return {"message": "Tarifa eliminada"}
