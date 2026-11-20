from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.user_model import User
from app.schemas.auth_schemas import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user_schemas import UserOut
from app.services.auth_service import login_user, revoke_refresh_token, rotate_refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_response(tokens: tuple[str, str]) -> TokenResponse:
    access, refresh = tokens
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    tokens = login_user(db, body.email, body.password)
    if tokens is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    tokens = rotate_refresh_token(db, body.refresh_token)
    if tokens is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _token_response(tokens)


@router.post("/logout", status_code=204)
def logout(body: RefreshRequest, db: Session = Depends(get_db)) -> Response:
    revoke_refresh_token(db, body.refresh_token)
    return Response(status_code=204)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user