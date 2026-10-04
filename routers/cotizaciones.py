import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models.cliente import Cliente
from models.cotizacion import Cotizacion
from schemas.cotizacion import CambioEstado, CotizacionCreate, CotizacionOut, CotizacionResumen, CotizacionUpdate
from services.cotizador import TRANSICIONES, aplicar_analisis, recalcular
from services.finanzas import TarifaFaltante
from services.similitud import similitud_coseno

logger = logging.getLogger("cotizador.api")
router = APIRouter(prefix="/cotizaciones", tags=["Quotes"])


def obtener_cotizacion(db: Session, cotizacion_id: int) -> Cotizacion:
    cot = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not cot:
        raise HTTPException(status_code=404, detail="Quote not found")
    return cot


def exigir_borrador(cot: Cotizacion) -> None:
    if cot.estado != "borrador":
        raise HTTPException(status_code=409, detail=f"The quote is '{cot.estado}': it can only be edited as a draft")


def guardar_recalculada(db: Session, cot: Cotizacion) -> Cotizacion:
    """Recalcula y guarda; si falta una tarifa deshace todo y responde 409."""
    try:
        recalcular(db, cot)
    except TarifaFaltante as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"{e}. Register it at /tarifas.")
    db.commit()
    db.refresh(cot)
    return cot


@router.post("", response_model=CotizacionOut, status_code=201)
def crear_cotizacion(datos: CotizacionCreate, db: Session = Depends(get_db)):
    if not db.query(Cliente).filter(Cliente.id == datos.cliente_id).first():
        raise HTTPException(status_code=404, detail="Client not found")
    cot = Cotizacion(**datos.model_dump())
    db.add(cot)
    db.commit()
    db.refresh(cot)
    return cot


@router.get("", response_model=list[CotizacionResumen])
def listar_cotizaciones(
    estado: str | None = None,
    cliente_id: int | None = None,
    db: Session = Depends(get_db),
):
    consulta = db.query(Cotizacion)
    if estado:
        consulta = consulta.filter(Cotizacion.estado == estado)
    if cliente_id:
        consulta = consulta.filter(Cotizacion.cliente_id == cliente_id)
    return consulta.order_by(Cotizacion.id.desc()).all()


@router.get("/{cotizacion_id}", response_model=CotizacionOut)
def ver_cotizacion(cotizacion_id: int, db: Session = Depends(get_db)):
    return obtener_cotizacion(db, cotizacion_id)


@router.put("/{cotizacion_id}", response_model=CotizacionOut)
def actualizar_cotizacion(cotizacion_id: int, datos: CotizacionUpdate, db: Session = Depends(get_db)):
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        if valor is not None:
            setattr(cot, campo, valor)
    return guardar_recalculada(db, cot)


@router.delete("/{cotizacion_id}")
def eliminar_cotizacion(cotizacion_id: int, db: Session = Depends(get_db)):
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    db.delete(cot)
    db.commit()
    return {"mensaje": "Quote deleted"}


@router.post("/{cotizacion_id}/analizar", response_model=CotizacionOut)
def analizar_cotizacion(cotizacion_id: int, db: Session = Depends(get_db)):
    """Runs the AI: detects modules, estimates hours with PERT and calculates the price."""
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    analisis = aplicar_analisis(cot)
    if not analisis["modulos"]:
        raise HTTPException(status_code=422, detail=" ".join(analisis["advertencias"]))
    logger.info("Quote %s analyzed: %s modules", cot.id, len(analisis["modulos"]))
    return guardar_recalculada(db, cot)


@router.get("/{cotizacion_id}/resumen")
def resumen_cotizacion(cotizacion_id: int, db: Session = Depends(get_db)):
    """Compact view for cards and dashboards: totals, hours, duration and confidence."""
    cot = obtener_cotizacion(db, cotizacion_id)
    est, fin = cot.estimacion or {}, cot.financiero or {}
    return {
        "id": cot.id,
        "titulo": cot.titulo,
        "cliente": cot.cliente.nombre,
        "estado": cot.estado,
        "modulos": sum(1 for i in cot.items if i.categoria != "Cross-cutting"),
        "horas_esperadas": est.get("horas_esperadas", 0),
        "rango_horas": [est.get("horas_optimista", 0), est.get("horas_pesimista", 0)],
        "confianza": est.get("confianza"),
        "duracion_semanas": fin.get("duracion_semanas", 0),
        "total": cot.total,
        "tiene_propuesta": bool(cot.propuesta),
    }


@router.post("/{cotizacion_id}/estado", response_model=CotizacionOut)
def cambiar_estado(cotizacion_id: int, datos: CambioEstado, db: Session = Depends(get_db)):
    cot = obtener_cotizacion(db, cotizacion_id)
    if datos.estado not in TRANSICIONES[cot.estado]:
        permitidos = ", ".join(sorted(TRANSICIONES[cot.estado])) or "none (final state)"
        raise HTTPException(status_code=409, detail=f"Cannot move from '{cot.estado}' to '{datos.estado}'. Allowed: {permitidos}")
    if datos.estado == "enviada" and not cot.propuesta:
        raise HTTPException(status_code=409, detail="Generate the proposal before sending the quote")
    cot.estado = datos.estado
    db.commit()
    db.refresh(cot)
    logger.info("Quote %s -> %s", cot.id, cot.estado)
    return cot


@router.get("/{cotizacion_id}/similares")
def cotizaciones_similares(cotizacion_id: int, limite: int = Query(3, ge=1, le=10), db: Session = Depends(get_db)):
    """Previous quotes with a similar scope (TF-IDF + cosine): useful as a price reference."""
    cot = obtener_cotizacion(db, cotizacion_id)
    otras = db.query(Cotizacion).filter(Cotizacion.id != cot.id).all()
    corpus = [o.descripcion_alcance for o in otras]
    puntuadas = [
        {
            "id": o.id,
            "titulo": o.titulo,
            "estado": o.estado,
            "total": o.total,
            "similitud": similitud_coseno(cot.descripcion_alcance, o.descripcion_alcance, corpus),
        }
        for o in otras
    ]
    puntuadas = [p for p in puntuadas if p["similitud"] > 0]
    return sorted(puntuadas, key=lambda p: p["similitud"], reverse=True)[:limite]
