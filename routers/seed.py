from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from services.seed import borrar_todo, cargar_datos_demo, hay_datos

router = APIRouter(tags=["Demo data"])


@router.post("/seed")
def cargar_seed(reiniciar: bool = False, db: Session = Depends(get_db)):
    if hay_datos(db):
        if not reiniciar:
            raise HTTPException(
                status_code=409,
                detail="Data is already loaded. Use /seed?reiniciar=true to delete it and load the demo data.",
            )
        borrar_todo(db)
    return {"mensaje": "Demo data loaded", "resumen": cargar_datos_demo(db)}
