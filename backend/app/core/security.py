import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import bcrypt
from jose import jwt

from app.core.config import settings

# NFR-03: BCrypt work factor 12
BCRYPT_ROUNDS = 12
# Gioi han cua thuat toan BCrypt: chi su dung 72 byte dau tien cua mat khau
BCRYPT_MAX_PASSWORD_BYTES = 72

ACCESS_TOKEN_TYPE = "access"


def utcnow() -> datetime:
    """Thoi diem hien tai theo UTC dang naive (cot DateTime MySQL khong luu timezone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ------------------------------------------------------------------------------
# Mat khau (BCrypt)
# ------------------------------------------------------------------------------

def get_password_hash(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        # Hash trong CSDL khong dung dinh dang BCrypt
        return False


# Hash gia dung de so sanh khi email khong ton tai -> thoi gian phan hoi dong deu,
# tranh lo thong tin email nao da dang ky (user enumeration qua timing).
_DUMMY_PASSWORD_HASH = get_password_hash(secrets.token_urlsafe(16))


def verify_dummy_password(plain_password: str) -> None:
    verify_password(plain_password, _DUMMY_PASSWORD_HASH)


# ------------------------------------------------------------------------------
# JWT Access Token (BR-10: 15 phut)
# ------------------------------------------------------------------------------

def create_access_token(
    subject: str | Any,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        **(extra_claims or {}),
        "sub": str(subject),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Giai ma va xac minh chu ky + han dung. Nem jose.JWTError neu token khong hop le."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ------------------------------------------------------------------------------
# Refresh Token (BR-10: 7 ngay) - chuoi ngau nhien, CSDL chi luu ban bam SHA-256
# ------------------------------------------------------------------------------

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
