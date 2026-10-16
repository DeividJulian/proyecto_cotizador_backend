"""Tarifas por hora de cada usuario. Arrancan con valores de referencia del mercado colombiano (COP)."""
from sqlalchemy.orm import Session

from models.tarifa import Tarifa
from models.usuario import Usuario
from services.catalogo import ROLES

TARIFAS_MERCADO = dict(zip(ROLES, [55_000, 50_000, 45_000, 40_000, 60_000, 65_000]))


def tarifas_de(db: Session, usuario_id: int) -> dict[str, int]:
    return {t.rol: t.valor_hora for t in db.query(Tarifa).filter(Tarifa.usuario_id == usuario_id).all()}


def crear_tarifas_iniciales(db: Session, usuario: Usuario) -> None:
    for rol, valor in TARIFAS_MERCADO.items():
        db.add(Tarifa(usuario_id=usuario.id, rol=rol, valor_hora=valor))


def restablecer_tarifas(db: Session, usuario: Usuario) -> None:
    """Borra las tarifas del usuario y vuelve a cargar las de mercado."""
    db.query(Tarifa).filter(Tarifa.usuario_id == usuario.id).delete()
    crear_tarifas_iniciales(db, usuario)
