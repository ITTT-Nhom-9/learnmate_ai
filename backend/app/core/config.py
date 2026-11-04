from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnMate AI - Backend Core"
    API_V1_STR: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = Field(
        default="mysql+pymysql://learnmate_user:learnmate_pass@localhost:3307/learnmate?charset=utf8mb4"
    )
    
    # Security & JWT
    JWT_SECRET: str = Field(default="YourSuperSecretKeyMin32Chars2026!")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Internal communication
    INTERNAL_API_KEY: str = Field(default="LM_Internal_Key_987654")
    AI_SERVICE_URL: str = Field(default="http://localhost:8000")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

