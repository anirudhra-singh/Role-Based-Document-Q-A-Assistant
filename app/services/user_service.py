import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user_model import User
from app.schemas.user_schemas import UserCreate, UserUpdate
from app.services.auth_service import revoke_all_refresh_tokens


class SelfModificationError(Exception):
    """An admin tried to change their own account."""


def create_user(db: Session, data: UserCreate) -> User | None:
    email = data.email.strip().lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        return None

    user = User(
        email=email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        role=data.role,
        department=data.department,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  
        db.rollback()
        return None
    db.refresh(user)
    return user


def list_users(db: Session, limit: int, offset: int) -> list[User]:
    stmt = select(User).order_by(User.created_at, User.id).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def update_user(
    db: Session, acting_admin_id: uuid.UUID, user_id: uuid.UUID, data: UserUpdate
) -> User | None:
    if user_id == acting_admin_id:
        raise SelfModificationError

    user = db.get(User, user_id)
    if user is None:
        return None

    changes = data.model_dump(exclude_unset=True) 
    for field, value in changes.items():
        setattr(user, field, value)

    if changes.get("is_active") is False:
        revoke_all_refresh_tokens(db, user.id)

    db.commit()
    db.refresh(user)
    return user