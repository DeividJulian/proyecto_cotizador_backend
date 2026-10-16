from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.tarifa import Tarifa
from models.usuario import Usuario
from schemas.tarifa import TarifaCreate, TarifaOut
from seguridad import usuario_actual
from services.tarifas import TARIFAS_MERCADO, restablecer_tarifas

router = APIRouter(prefix="/tarifas", tags=["Rates"])


def rol_en_uso(db: Session, usuario_id: int, rol: str, excluir_id: int | None = None) -> bool:
    consulta = db.query(Tarifa).filter(Tarifa.usuario_id == usuario_id, func.lower(Tarifa.rol) == rol.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Tarifa.id != excluir_id)
    return consulta.first() is not None


def obtener_tarifa(db: Session, tarifa_id: int, usuario: Usuario) -> Tarifa:
    tarifa = db.query(Tarifa).filter(Tarifa.id == tarifa_id, Tarifa.usuario_id == usuario.id).first()
    if not tarifa:
        raise HTTPException(status_code=404, detail="Rate not found")
    return tarifa


@router.get("", response_model=list[TarifaOut])
def listar_tarifas(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    return db.query(Tarifa).filter(Tarifa.usuario_id == usuario.id).order_by(Tarifa.id).all()


@router.get("/mercado")
def tarifas_de_mercado():
    """Reference hourly rates (COP) loaded for every new account."""
    return [{"rol": rol, "valor_hora": valor} for rol, valor in TARIFAS_MERCADO.items()]


@router.post("", response_model=TarifaOut, status_code=201)
def crear_tarifa(datos: TarifaCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    if rol_en_uso(db, usuario.id, datos.rol):
        raise HTTPException(status_code=409, detail="You already have a rate for that role")
    tarifa = Tarifa(usuario_id=usuario.id, rol=datos.rol, valor_hora=datos.valor_hora)
    db.add(tarifa)
    db.commit()
    db.refresh(tarifa)
    return tarifa


@router.post("/restablecer", response_model=list[TarifaOut])
def restablecer(db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    """Replaces your rates with the market reference rates."""
    restablecer_tarifas(db, usuario)
    db.commit()
    return db.query(Tarifa).filter(Tarifa.usuario_id == usuario.id).order_by(Tarifa.id).all()


@router.put("/{tarifa_id}", response_model=TarifaOut)
def actualizar_tarifa(
    tarifa_id: int, datos: TarifaCreate, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)
):
    tarifa = obtener_tarifa(db, tarifa_id, usuario)
    if rol_en_uso(db, usuario.id, datos.rol, excluir_id=tarifa_id):
        raise HTTPException(status_code=409, detail="You already have another rate for that role")
    tarifa.rol = datos.rol
    tarifa.valor_hora = datos.valor_hora
    db.commit()
    db.refresh(tarifa)
    return tarifa


@router.delete("/{tarifa_id}")
def eliminar_tarifa(tarifa_id: int, db: Session = Depends(get_db), usuario: Usuario = Depends(usuario_actual)):
    tarifa = obtener_tarifa(db, tarifa_id, usuario)
    db.delete(tarifa)
    db.commit()
    return {"mensaje": "Rate deleted"}
