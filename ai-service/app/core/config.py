from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Xác định đường dẫn gốc để tự động đọc .env bất kể thư mục thực thi lệnh
CORE_DIR = Path(__file__).resolve().parent
AI_SERVICE_DIR = CORE_DIR.parent.parent
REPO_ROOT = AI_SERVICE_DIR.parent

ENV_FILES: List[str] = [
    str(REPO_ROOT / ".env"),
    str(AI_SERVICE_DIR / ".env"),
    ".env",
    "../.env",
]


class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnMate AI - AI Microservice"
    INTERNAL_API_KEY: str = Field(default="LM_Internal_Key_987654")

    # LLM Settings
    LLM_PROVIDER: str = Field(default="gemini")
    LLM_MODEL: str = Field(default="gemini-3.5-flash-lite")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)

    # Circuit Breaker & Timeout (Theo SDD Bảng 3 & Bảng 20)
    AI_TIMEOUT_SECONDS: float = Field(default=35.0, ge=1.0, le=120.0)
    MAX_RETRIES: int = Field(default=2, ge=0, le=5)
    CIRCUIT_BREAKER_THRESHOLD: int = Field(default=5, ge=1, le=50)
    CIRCUIT_BREAKER_RESET_SECONDS: float = Field(default=60.0, ge=1.0, le=600.0)

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
