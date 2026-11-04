from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator
from typing import Optional


class Settings(BaseSettings):
    PROJECT_NAME: str = "LearnMate AI - Backend Core"
    API_V1_STR: str = "/api/v1"
    
    # Database Settings
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
                f"@localhost:{self.MYSQL_HOST_PORT}/{self.DB_NAME}?charset=utf8mb4"
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

