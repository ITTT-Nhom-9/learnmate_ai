from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.security import BCRYPT_MAX_PASSWORD_BYTES

PASSWORD_MIN_LENGTH = 8


# ------------------------------------------------------------------------------
# Request DTO
# ------------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    full_name: str = Field(..., min_length=1, max_length=150)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Họ tên không được để trống")
        return v

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str) -> str:
        if len(v.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
            raise ValueError(f"Mật khẩu không được vượt quá {BCRYPT_MAX_PASSWORD_BYTES} byte")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# ------------------------------------------------------------------------------
# Response DTO
# ------------------------------------------------------------------------------

class RegisterResponse(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: str
    created_at: datetime


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Thời gian sống của Access Token (giây)")


class LoginResponse(TokenResponse):
    user: UserBrief


class LogoutResponse(BaseModel):
    revoked: bool
    message: str
