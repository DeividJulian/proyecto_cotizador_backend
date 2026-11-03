"""FastAPI dependency that requires a logged-in user."""
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from services.auth import read_token

bearer = HTTPBearer(auto_error=False, description="Token que devuelve /auth/verify")

NO_SESSION = "Debes iniciar sesión"
INVALID_SESSION = "La sesión venció o no es válida: inicia sesión de nuevo"


def user_from_token(db: Session, token: str) -> User | None:
    """The verified owner of a valid, unexpired token. Shared by the REST API and the gRPC services."""
    user_id = read_token(token)
    user = db.get(User, user_id) if user_id is not None else None
    return user if user is not None and user.verified else None


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail=NO_SESSION, headers={"WWW-Authenticate": "Bearer"})
    user = user_from_token(db, credentials.credentials)
    if user is None:
        raise HTTPException(status_code=401, detail=INVALID_SESSION, headers={"WWW-Authenticate": "Bearer"})
    return user
