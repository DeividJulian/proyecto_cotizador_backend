"""Hourly rates of each user. They start with reference values of the Colombian market (COP)."""
from sqlalchemy.orm import Session

from models.rate import Rate
from models.user import User
from services.catalog import ROLES

MARKET_RATES = dict(zip(ROLES, [55_000, 50_000, 45_000, 40_000, 60_000, 65_000]))


def rates_of(db: Session, user_id: int) -> dict[str, int]:
    return {r.role: r.hourly_rate for r in db.query(Rate).filter(Rate.user_id == user_id).all()}


def create_initial_rates(db: Session, user: User) -> None:
    for role, value in MARKET_RATES.items():
        db.add(Rate(user_id=user.id, role=role, hourly_rate=value))


def reset_rates(db: Session, user: User) -> None:
    """Deletes the user's rates and loads the market ones again."""
    db.query(Rate).filter(Rate.user_id == user.id).delete()
    create_initial_rates(db, user)
