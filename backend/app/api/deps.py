from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.security import ACCESS_TOKEN_TYPE, decode_token, JWTError
from app.models.user import User, UserRole, UserStatus


bearer_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR.lstrip('/')}/auth/token", auto_error=False
)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: str | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Xac thuc Access Token tu header Authorization: Bearer <JWT>."""
    if not token:
        raise _unauthorized("Thiếu Access Token")

    try:
        payload = decode_token(token)
    except JWTError:
        raise _unauthorized("Access Token không hợp lệ hoặc đã hết hạn")

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise _unauthorized("Sai loại token")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise _unauthorized("Access Token không hợp lệ")

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized("Người dùng không tồn tại")
    if user.status != UserStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Xác thực người dùng có vai trò Quản trị viên (ADMIN)."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ Quản trị viên (ADMIN) mới có quyền truy cập chức năng này",
        )
    return current_user


get_current_admin = require_admin

