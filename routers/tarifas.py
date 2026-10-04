from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.tarifa import Tarifa
from schemas.tarifa import TarifaCreate, TarifaOut

router = APIRouter(prefix="/tarifas", tags=["Rates"])


def rol_en_uso(db: Session, rol: str, excluir_id: int | None = None) -> bool:
    consulta = db.query(Tarifa).filter(func.lower(Tarifa.rol) == rol.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Tarifa.id != excluir_id)
    return consulta.first() is not None


def obtener_tarifa(db: Session, tarifa_id: int) -> Tarifa:
    tarifa = db.query(Tarifa).filter(Tarifa.id == tarifa_id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Rate not found")
    return tarifa


@router.post("", response_model=TarifaOut, status_code=201)
def crear_tarifa(datos: TarifaCreate, db: Session = Depends(get_db)):
    if rol_en_uso(db, datos.rol):
        raise HTTPException(status_code=409, detail="A rate for that role already exists")
    tarifa = Tarifa(rol=datos.rol, valor_hora=datos.valor_hora)
    db.add(tarifa)
    db.commit()
    db.refresh(tarifa)
    return tarifa


@router.get("", response_model=list[TarifaOut])
def listar_tarifas(db: Session = Depends(get_db)):
    return db.query(Tarifa).order_by(Tarifa.id).all()


@router.put("/{tarifa_id}", response_model=TarifaOut)
def actualizar_tarifa(tarifa_id: int, datos: TarifaCreate, db: Session = Depends(get_db)):
    tarifa = obtener_tarifa(db, tarifa_id)
    if rol_en_uso(db, datos.rol, excluir_id=tarifa_id):
        raise HTTPException(status_code=409, detail="Another rate for that role already exists")
    tarifa.rol = datos.rol
    tarifa.valor_hora = datos.valor_hora
    db.commit()
    db.refresh(tarifa)
    return tarifa


@router.delete("/{tarifa_id}")
def eliminar_tarifa(tarifa_id: int, db: Session = Depends(get_db)):
    tarifa = obtener_tarifa(db, tarifa_id)
    db.delete(tarifa)
    db.commit()
    return {"mensaje": "Rate deleted"}
