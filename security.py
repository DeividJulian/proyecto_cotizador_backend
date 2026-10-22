"""FastAPI dependency that requires a logged-in user."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.auth import read_token

bearer = HTTPBearer(auto_error=False, description="Token returned by /auth/verify")


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión", headers={"WWW-Authenticate": "Bearer"})
    user_id = read_token(credentials.credentials)
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.verified:
        raise HTTPException(
            status_code=401,
            detail="La sesión venció o no es válida: inicia sesión de nuevo",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
