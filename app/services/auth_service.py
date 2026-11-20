import uuid
from datetime import datetime, timezone

import jwt
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    verify_password,
)
from app.models.refresh_token_model import RefreshToken
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


def _issue_tokens(db: Session, user: User) -> tuple[str, str]:
    """Create an access + refresh token and record the refresh jti. Caller commits."""
    access = create_access_token(user.id)
    refresh, jti, expires_at = create_refresh_token(user.id)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=expires_at))
    return access, refresh


def _revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )


def login_user(db: Session, email: str, password: str) -> tuple[str, str] | None:
    user = authenticate(db, email, password)
    if user is None:
        return None
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def rotate_refresh_token(db: Session, token: str) -> tuple[str, str] | None:
    """Use a refresh token once and return a new (access, refresh) pair, or None."""
    try:
        payload = decode_refresh_token(token)
        jti = payload["jti"]
        user_id = uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None

    # Lock the row so two simultaneous refreshes can't both succeed.
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti).with_for_update())
    if row is None or row.user_id != user_id:
        return None

    now = datetime.now(timezone.utc)

    if row.revoked_at is not None:
        # A used token came back: possible theft. End every session of this user.
        _revoke_all_for_user(db, row.user_id)
        db.commit()
        return None

    if row.expires_at <= now:
        return None

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        return None

    row.revoked_at = now
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens


def revoke_refresh_token(db: Session, token: str) -> None:
    """Logout. Silently does nothing if the token is bad, so it reveals nothing."""
    try:
        jti = decode_refresh_token(token)["jti"]
    except (jwt.InvalidTokenError, KeyError):
        return
    row = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if row is not None and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()