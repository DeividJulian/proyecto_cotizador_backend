from fastapi import APIRouter, Depends, HTTPException

from schemas.common import errors
from schemas.scope import Analysis, ScopeEstimate, ScopeInput
from security import current_user
from services.estimation import build_items, summarize_estimate
from services.scope import analyze_scope

router = APIRouter(prefix="/scope", tags=["Alcance"], dependencies=[Depends(current_user)], responses=errors(401, 422))


@router.post("/analyze", response_model=Analysis, summary="Analizar alcance")
def analyze_scope_text(data: ScopeInput):
    """Detecta los módulos, la complejidad y la confianza de una descripción de proyecto (no guarda nada)."""
    return analyze_scope(data.scope_description)


@router.post("/estimate", response_model=ScopeEstimate, summary="Estimar alcance")
def estimate_scope(data: ScopeInput):
    """Estima las horas por módulo y por rol con PERT (no guarda nada)."""
    analysis = analyze_scope(data.scope_description)
    if not analysis["modules"]:
        raise HTTPException(status_code=422, detail=" ".join(analysis["warnings"]))
    items = build_items(analysis["modules"])
    return {"analysis": analysis, "items": items, "estimate": summarize_estimate(items, analysis["confidence"])}
