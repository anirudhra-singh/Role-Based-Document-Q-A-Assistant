import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

ALGORITHM = "HS256"

_password_hash = PasswordHash.recommended()  # Argon2id

# Used to spend the same time when the email doesn't exist (see auth_service).
DUMMY_HASH = _password_hash.hash("dummy-password-for-timing")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_hash.verify(password, password_hash)


def _secret() -> str:
    return get_settings().secret_key.get_secret_value()


def create_access_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=get_settings().access_token_expire_minutes),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at). The jti is what we store in the database."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=get_settings().refresh_token_expire_days)
    jti = uuid.uuid4().hex
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM), jti, expires_at


def _decode(token: str, expected_type: str, required: list[str]) -> dict:
    payload = jwt.decode(
        token, _secret(), algorithms=[ALGORITHM], options={"require": required}
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError (or a subclass) if bad, expired or the wrong type."""
    return _decode(token, "access", ["exp", "iat", "sub"])


def decode_refresh_token(token: str) -> dict:
    return _decode(token, "refresh", ["exp", "iat", "sub", "jti"])