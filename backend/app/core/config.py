import os
from pathlib import Path
from typing import Optional, List
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Xac dinh duong dan goc de tu dong doc .env bat ke thu muc thuc thi lenh
CORE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CORE_DIR.parent.parent
REPO_ROOT = BACKEND_DIR.parent

ENV_FILES: List[str] = [
    str(REPO_ROOT / ".env"),
    str(BACKEND_DIR / ".env"),
    ".env",
    "../.env",
]


class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnMate AI - Backend Core"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
    DB_HOST: str = Field(default="localhost")
    DB_USER: str = Field(default="learnmate_user")
    DB_PASSWORD: str = Field(default="your_secure_password")
    DB_NAME: str = Field(default="learnmate")
    MYSQL_HOST_PORT: int = Field(default=3306)
    DATABASE_URL: Optional[str] = None
    
    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if not self.DATABASE_URL:
            self.DATABASE_URL = (
                f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
                f"@{self.DB_HOST}:{self.MYSQL_HOST_PORT}/{self.DB_NAME}?charset=utf8mb4"
            )
        return self
    
    # Security & JWT
    JWT_SECRET: str = Field(default="YourSuperSecretKeyMin32Chars2026!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Internal communication
    INTERNAL_API_KEY: str = Field(default="LM_Internal_Key_987654")
    AI_SERVICE_URL: str = Field(default="http://localhost:8000")
    AI_SERVICE_TIMEOUT_SECONDS: float = Field(default=60.0)

    # AI Tutor - QuotaGuard (BR-05): so cau hoi toi da moi sinh vien / ngay (theo gio Viet Nam)
    TUTOR_DAILY_QUOTA: int = Field(default=50)
    TUTOR_HISTORY_WINDOW: int = Field(default=10)

    # CORS: danh sach origin Frontend, phan tach boi dau phay.
    # Khong dung "*" vi allow_credentials=True (trinh duyet se chan theo chuan W3C CORS).
    CORS_ORIGINS: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:3000,http://127.0.0.1:3000"
        )
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
