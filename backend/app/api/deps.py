from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ACCESS_TOKEN_TYPE, decode_token, JWTError
from app.models.user import User, UserRole, UserStatus


bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Xac thuc Access Token tu header Authorization: Bearer <JWT>."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Thiếu Access Token")

    try:
        payload = decode_token(credentials.credentials)
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

