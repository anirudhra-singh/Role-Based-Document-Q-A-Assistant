import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_roles
from app.models.user_model import User
from app.schemas.user_schemas import UserAdminOut, UserCreate, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/admin", tags=["admin"])

require_admin = require_roles("admin")


@router.post(
    "/users",
    response_model=UserAdminOut,
    status_code=201,
    dependencies=[Depends(require_admin)],
)
def create_user(body: UserCreate, db: Session = Depends(get_db)) -> User:
    user = user_service.create_user(db, body)
    if user is None:
        raise HTTPException(status_code=409, detail="A user with this email already exists")
    return user


@router.get(
    "/users",
    response_model=list[UserAdminOut],
    dependencies=[Depends(require_admin)],
)
def list_users(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> list[User]:
    return user_service.list_users(db, limit, offset)


@router.patch("/users/{user_id}", response_model=UserAdminOut)
def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    try:
        user = user_service.update_user(db, admin.id, user_id, body)
    except user_service.SelfModificationError:
        raise HTTPException(status_code=400, detail="You cannot change your own account")
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user