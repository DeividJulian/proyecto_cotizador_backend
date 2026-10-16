from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.usuario import Usuario
from schemas.auth import CambioRol, UsuarioOut
from seguridad import solo_admin
from services.auth import vincular_cliente

router = APIRouter(prefix="/usuarios", tags=["Users"], dependencies=[Depends(solo_admin)])


@router.get("", response_model=list[UsuarioOut])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(Usuario).order_by(Usuario.id).all()


@router.put("/{usuario_id}/rol", response_model=UsuarioOut)
def cambiar_rol(usuario_id: int, datos: CambioRol, db: Session = Depends(get_db), admin: Usuario = Depends(solo_admin)):
    """Promotes a user to administrator or turns them into a client."""
    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="User not found")
    if usuario.id == admin.id:
        raise HTTPException(status_code=409, detail="You cannot change your own role")
    usuario.rol = datos.rol
    if usuario.verificado:
        vincular_cliente(db, usuario)
    db.commit()
    db.refresh(usuario)
    return usuario
