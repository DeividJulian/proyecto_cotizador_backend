"""Demo account for presenting the project (DEMO_ACCOUNTS, DEMO_ADMIN_EMAIL, DEMO_PASSWORD).

Everybody else keeps logging in with an emailed code. The demo account is the only one that accepts a password, and
it is a normal user: the project has no roles. Its inbox is not ours, so nothing is ever sent to that address.
"""
import functools
import hashlib
import hmac
import logging
import os

from sqlalchemy.orm import Session

import config
from models.user import User
from services.finance import MissingRate
from services.rates import create_initial_rates
from services.seed import has_quotes, load_examples

logger = logging.getLogger("cotizador.demo")

DEMO_NAME = "Cuenta de demostración"
_ITERATIONS = 200_000
_SALT = os.urandom(16)  # new on every start: the hash never leaves memory


def _hash(password: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), _SALT, _ITERATIONS)


@functools.lru_cache(maxsize=4)
def _expected_hash(password: str) -> bytes:
    """Hash of DEMO_PASSWORD, computed once per value."""
    return _hash(password)


def demo_emails() -> set[str]:
    """Addresses that must never receive an email, even with DEMO_ACCOUNTS=false."""
    return {config.DEMO_ADMIN_EMAIL}


def is_demo_email(email: str | None) -> bool:
    return (email or "").strip().lower() in demo_emails()


def check_password(email: str, password: str) -> bool:
    """True only for a demo address, with the demo password, while DEMO_ACCOUNTS is on."""
    if not config.DEMO_ACCOUNTS or not is_demo_email(email):
        return False
    return hmac.compare_digest(_hash(password), _expected_hash(config.DEMO_PASSWORD))


def ensure_demo_accounts(db: Session) -> None:
    """Creates the demo account with its rates and the example quotes if it does not exist yet."""
    if not config.DEMO_ACCOUNTS:
        return
    email = config.DEMO_ADMIN_EMAIL
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=DEMO_NAME, email=email)
        db.add(user)
        db.flush()
    if not user.verified:
        user.verified = True
        create_initial_rates(db, user)
        db.flush()
    if not has_quotes(db, user.id):
        try:
            load_examples(db, user)
        except MissingRate:
            logger.warning("The demo account has no rate for some role: no example quotes were loaded")
    db.commit()
