import uuid
from collections.abc import Callable, Generator

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user_model import User

# auto_error=False so WE decide the response and it is always a plain 401.
bearer_scheme = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Identity comes from the token. Role and department come from the DATABASE, every time."""
    if credentials is None:
        raise _unauthorized()
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _unauthorized()

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


def require_roles(*allowed_roles: str) -> Callable[..., User]:
    """Use as: Depends(require_roles("admin", "hr")). Wrong role gives 403."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return checker