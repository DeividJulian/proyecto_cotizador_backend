from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from models.cliente import Cliente
from models.cotizacion import Cotizacion
from schemas.cliente import ClienteCreate, ClienteOut

router = APIRouter(prefix="/clientes", tags=["Clients"])


def correo_en_uso(db: Session, email: str, excluir_id: int | None = None) -> bool:
    consulta = db.query(Cliente).filter(func.lower(Cliente.email) == email.lower())
    if excluir_id is not None:
        consulta = consulta.filter(Cliente.id != excluir_id)
    return consulta.first() is not None


def obtener_cliente(db: Session, cliente_id: int) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Client not found")
    return cliente


@router.post("", response_model=ClienteOut, status_code=201)
def crear_cliente(datos: ClienteCreate, db: Session = Depends(get_db)):
    if correo_en_uso(db, datos.email):
        raise HTTPException(status_code=409, detail="A client with that email already exists")
    cliente = Cliente(**datos.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.get("", response_model=list[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(Cliente).order_by(Cliente.id).all()


@router.get("/{cliente_id}", response_model=ClienteOut)
def obtener(cliente_id: int, db: Session = Depends(get_db)):
    return obtener_cliente(db, cliente_id)


@router.put("/{cliente_id}", response_model=ClienteOut)
def actualizar_cliente(cliente_id: int, datos: ClienteCreate, db: Session = Depends(get_db)):
    cliente = obtener_cliente(db, cliente_id)
    if correo_en_uso(db, datos.email, excluir_id=cliente_id):
        raise HTTPException(status_code=409, detail="Another client with that email already exists")
    for campo, valor in datos.model_dump().items():
        setattr(cliente, campo, valor)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/{cliente_id}")
def eliminar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = obtener_cliente(db, cliente_id)
    if db.query(Cotizacion).filter(Cotizacion.cliente_id == cliente_id).first():
        raise HTTPException(status_code=409, detail="Cannot delete: the client has quotes")
    db.delete(cliente)
    db.commit()
    return {"mensaje": "Client deleted"}
