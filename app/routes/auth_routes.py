from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import DUMMY_HASH, verify_password
from app.models.user_model import User


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Return the user if the credentials are valid, else None. Never says which part was wrong."""
    user = db.scalar(select(User).where(User.email == email.strip().lower()))

    if user is None:
        verify_password(password, DUMMY_HASH)  # same work as a real check
        return None

    password_ok = verify_password(password, user.password_hash)
    if not password_ok or not user.is_active:
        return None
    return user