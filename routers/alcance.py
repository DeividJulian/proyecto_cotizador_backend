from fastapi import APIRouter, HTTPException

from schemas.alcance import AlcanceEntrada
from services.alcance import analizar_alcance
from services.estimacion import construir_items, resumen_estimacion

router = APIRouter(prefix="/alcance", tags=["Scope"])


@router.post("/analizar")
def analizar(entrada: AlcanceEntrada):
    """Detects the modules, complexity and confidence of a project description (nothing is saved)."""
    return analizar_alcance(entrada.descripcion_alcance)


@router.post("/estimar")
def estimar(entrada: AlcanceEntrada):
    """Estimates hours per module and per role with PERT (nothing is saved)."""
    analisis = analizar_alcance(entrada.descripcion_alcance)
    if not analisis["modulos"]:
        raise HTTPException(status_code=422, detail=" ".join(analisis["advertencias"]))
    items = construir_items(analisis["modulos"])
    return {
        "analisis": analisis,
        "items": items,
        "estimacion": resumen_estimacion(items, analisis["confianza"]),
    }
