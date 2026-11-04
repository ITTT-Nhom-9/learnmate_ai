from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnMate AI - AI Microservice"
    INTERNAL_API_KEY: str = Field(default="LM_Internal_Key_987654")
    
    # LLM Settings
    LLM_PROVIDER: str = Field(default="gemini")
    LLM_MODEL: str = Field(default="gemini-3.5-flash-lite")
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GEMINI_API_KEY: Optional[str] = Field(default=None)
    
    # Circuit Breaker & Timeout
    AI_TIMEOUT_SECONDS: float = 35.0
    MAX_RETRIES: int = 2
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

