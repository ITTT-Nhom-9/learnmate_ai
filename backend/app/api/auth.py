from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    LogoutResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserBrief,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _to_http(exc: AuthError) -> HTTPException:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return HTTPException(status_code=exc.status_code, detail=exc.message, headers=headers)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="API-01: Đăng ký tài khoản sinh viên mới",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = AuthService(db).register(payload.email, payload.password, payload.full_name)
    except AuthError as exc:
        raise _to_http(exc)
    return RegisterResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at,
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="API-02: Đăng nhập, cấp cặp JWT Access (15p) & Refresh (7 ngày)",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        user, tokens = AuthService(db).login(payload.email, payload.password)
    except AuthError as exc:
        raise _to_http(exc)
    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserBrief.model_validate(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="API-03: Làm mới Access Token (Refresh Token Rotation)",
)
def refresh(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    try:
        tokens = AuthService(db).refresh(payload.refresh_token)
    except AuthError as exc:
        raise _to_http(exc)
    return TokenResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
    )


@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="API-04: Đăng xuất, thu hồi Refresh Token",
)
def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        AuthService(db).logout(current_user, payload.refresh_token)
    except AuthError as exc:
        raise _to_http(exc)
    return LogoutResponse(revoked=True, message="Đăng xuất thành công")
