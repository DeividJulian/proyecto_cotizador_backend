from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.quote import Quote, QuoteItem
from models.user import User
from routers.quotes import get_quote, require_draft, save_recalculated
from schemas.common import errors
from schemas.quote import ItemCreate, ItemOut, ItemUpdate, QuoteOut
from security import current_user
from services.estimation import manual_item

router = APIRouter(prefix="/quotes/{quote_id}/items", tags=["Módulos de la cotización"], responses=errors(401, 404, 409, 422))

EDITABLE_FIELDS = ("name", "complexity", "source", "split", "hours_optimistic", "hours_likely", "hours_pessimistic",
                   "hours_expected")


def validate_split(split: dict[str, float] | None) -> None:
    if split is None:
        return
    if any(v < 0 for v in split.values()) or abs(sum(split.values()) - 1) > 0.01:
        raise HTTPException(status_code=422, detail="El reparto por rol debe sumar 1 (100 %)")


def _find_item(quote: Quote, item_id: int) -> QuoteItem:
    item = next((i for i in quote.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Módulo no encontrado en esta cotización")
    return item


@router.get("", response_model=list[ItemOut], summary="Módulos")
def list_items(quote_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    return get_quote(db, quote_id, user).items


@router.post("", response_model=QuoteOut, status_code=201, summary="Agregar módulo")
def add_item(quote_id: int, data: ItemCreate, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    validate_split(data.split)
    quote.items.append(QuoteItem(**manual_item(data.name, data.category, data.complexity, data.hours_likely, data.split)))
    return save_recalculated(db, quote)


@router.put("/{item_id}", response_model=QuoteOut, summary="Ajustar módulo")
def update_item(
    quote_id: int, item_id: int, data: ItemUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)
):
    """Ajusta un módulo. Si venía del análisis pasa a manual, para que un nuevo análisis no lo pise."""
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    item = _find_item(quote, item_id)
    validate_split(data.split)
    changes = data.model_dump(exclude_unset=True)
    new = manual_item(
        changes.get("name") or item.name,
        item.category,
        changes.get("complexity") or item.complexity,
        changes.get("hours_likely") or item.hours_likely,
        changes.get("split") or item.split,
    )
    for field in EDITABLE_FIELDS:
        setattr(item, field, new[field])
    item.reasons = "Ajustado manualmente"
    return save_recalculated(db, quote)


@router.delete("/{item_id}", response_model=QuoteOut, summary="Quitar módulo")
def delete_item(quote_id: int, item_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    quote = get_quote(db, quote_id, user)
    require_draft(quote)
    quote.items.remove(_find_item(quote, item_id))
    return save_recalculated(db, quote)
