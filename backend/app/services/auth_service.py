from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_refresh_token,
    refresh_token_expiry,
    utcnow,
    verify_dummy_password,
    verify_password,
)
from app.models.user import RefreshToken, User, UserRole, UserStatus


class AuthError(Exception):
    """Loi nghiep vu xac thuc, router se anh xa sang HTTP status tuong ung."""

    status_code: int = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class EmailAlreadyExistsError(AuthError):
    status_code = 400  # Theo dac ta API-01


class InvalidCredentialsError(AuthError):
    status_code = 401


class AccountLockedError(AuthError):
    status_code = 403


class InvalidRefreshTokenError(AuthError):
    status_code = 401


@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------------------------
    # Dang ky
    # --------------------------------------------------------------------------
    def register(self, email: str, password: str, full_name: str) -> User:
        if self._get_user_by_email(email) is not None:
            raise EmailAlreadyExistsError("Email đã được đăng ký")

        user = User(
            email=email,
            password_hash=get_password_hash(password),
            full_name=full_name,
            role=UserRole.STUDENT.value,
            status=UserStatus.ACTIVE.value,
        )
        self.db.add(user)
        try:
            self.db.commit()
        except IntegrityError:
            # Hai request dang ky cung email dong thoi -> rang buoc UNIQUE chan lai
            self.db.rollback()
            raise EmailAlreadyExistsError("Email đã được đăng ký")
        self.db.refresh(user)
        return user

    # --------------------------------------------------------------------------
    # Dang nhap
    # --------------------------------------------------------------------------
    def login(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = self._get_user_by_email(email)
        if user is None:
            verify_dummy_password(password)
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Email hoặc mật khẩu không đúng")
        if user.status != UserStatus.ACTIVE.value:
            raise AccountLockedError("Tài khoản đã bị khóa")

        tokens = self._issue_token_pair(user)
        self.db.commit()
        return user, tokens

    # --------------------------------------------------------------------------
    # Lam moi token voi co che Rotation
    # --------------------------------------------------------------------------
    def refresh(self, raw_refresh_token: str) -> TokenPair:
        stored = self._get_refresh_token(raw_refresh_token, for_update=True)
        if stored is None:
            raise InvalidRefreshTokenError("Refresh token không hợp lệ")

        now = utcnow()
        if stored.revoked_at is not None:
            # Token da bi xoay vong/thu hoi nhung van duoc dung lai -> dau hieu bi danh cap.
            # Thu hoi toan bo phien cua nguoi dung de buoc dang nhap lai.
            self._revoke_all_user_tokens(stored.user_id, now)
            self.db.commit()
            raise InvalidRefreshTokenError("Refresh token đã bị thu hồi")
        if stored.expires_at <= now:
            raise InvalidRefreshTokenError("Refresh token đã hết hạn")

        user = stored.user
        if user.status != UserStatus.ACTIVE.value:
            self._revoke_all_user_tokens(user.id, now)
            self.db.commit()
            raise InvalidRefreshTokenError("Tài khoản đã bị khóa")

        # Rotation: huy token cu, phat hanh cap token moi
        stored.revoked_at = now
        tokens = self._issue_token_pair(user)
        self.db.commit()
        return tokens

    # --------------------------------------------------------------------------
    # Dang xuat
    # --------------------------------------------------------------------------
    def logout(self, user: User, raw_refresh_token: str) -> None:
        stored = self._get_refresh_token(raw_refresh_token, for_update=True)
        if stored is None or stored.user_id != user.id:
            raise InvalidRefreshTokenError("Refresh token không hợp lệ")
        if stored.revoked_at is None:
            stored.revoked_at = utcnow()
            self.db.commit()

    # --------------------------------------------------------------------------
    # Helpers
    # --------------------------------------------------------------------------
    def _get_user_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def _get_refresh_token(self, raw_token: str, for_update: bool = False) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        if for_update:
            # Khoa dong tren MySQL de 2 request refresh dong thoi khong cung xoay vong 1 token
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def _issue_token_pair(self, user: User) -> TokenPair:
        access_token = create_access_token(user.id, extra_claims={"role": user.role})
        raw_refresh = generate_refresh_token()
        self.db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(raw_refresh),
                expires_at=refresh_token_expiry(),
            )
        )
        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def _revoke_all_user_tokens(self, user_id: int, when) -> None:
        self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=when)
        )
