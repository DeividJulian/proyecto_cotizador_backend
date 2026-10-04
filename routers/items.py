from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.cotizacion import ItemCotizacion
from routers.cotizaciones import exigir_borrador, guardar_recalculada, obtener_cotizacion
from schemas.cotizacion import CotizacionOut, ItemCreate, ItemOut, ItemUpdate
from services.estimacion import item_manual

router = APIRouter(prefix="/cotizaciones/{cotizacion_id}/items", tags=["Quote items"])


def validar_distribucion(distribucion: dict[str, float] | None) -> None:
    if distribucion is None:
        return
    if any(v < 0 for v in distribucion.values()) or abs(sum(distribucion.values()) - 1) > 0.01:
        raise HTTPException(status_code=422, detail="The role distribution must add up to 1 (100%)")


@router.get("", response_model=list[ItemOut])
def listar_items(cotizacion_id: int, db: Session = Depends(get_db)):
    return obtener_cotizacion(db, cotizacion_id).items


@router.post("", response_model=CotizacionOut, status_code=201)
def agregar_item(cotizacion_id: int, datos: ItemCreate, db: Session = Depends(get_db)):
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    validar_distribucion(datos.distribucion)
    cot.items.append(
        ItemCotizacion(**item_manual(datos.nombre, datos.categoria, datos.complejidad, datos.horas_probable, datos.distribucion))
    )
    return guardar_recalculada(db, cot)


def _buscar_item(cot, item_id: int) -> ItemCotizacion:
    item = next((i for i in cot.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in this quote")
    return item


@router.put("/{item_id}", response_model=CotizacionOut)
def actualizar_item(cotizacion_id: int, item_id: int, datos: ItemUpdate, db: Session = Depends(get_db)):
    """Adjusts an item. If it came from the AI it becomes manual, so a new analysis won't overwrite it."""
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    item = _buscar_item(cot, item_id)
    validar_distribucion(datos.distribucion)
    cambios = datos.model_dump(exclude_unset=True)
    nuevo = item_manual(
        cambios.get("nombre") or item.nombre,
        item.categoria,
        cambios.get("complejidad") or item.complejidad,
        cambios.get("horas_probable") or item.horas_probable,
        cambios.get("distribucion") or item.distribucion,
    )
    for campo in ("nombre", "complejidad", "origen", "distribucion", "horas_optimista", "horas_probable",
                  "horas_pesimista", "horas_esperadas"):
        setattr(item, campo, nuevo[campo])
    item.motivos = "Adjusted manually"
    return guardar_recalculada(db, cot)


@router.delete("/{item_id}", response_model=CotizacionOut)
def eliminar_item(cotizacion_id: int, item_id: int, db: Session = Depends(get_db)):
    cot = obtener_cotizacion(db, cotizacion_id)
    exigir_borrador(cot)
    cot.items.remove(_buscar_item(cot, item_id))
    return guardar_recalculada(db, cot)
