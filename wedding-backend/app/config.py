from __future__ import annotations
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+asyncmy://root:root@localhost:3306/wedding"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10
    APP_NAME: str = "婚庆管理系统"
    DEBUG: bool = True
    SENTRY_DSN: str | None = None
    APP_ENV: str = "development"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    def validate_settings(self):
        if self.APP_ENV == "production" and self.JWT_SECRET == "change-me-in-production":
            raise ValueError("JWT_SECRET must be set to a secure value in production")


settings = Settings()
try:
    settings.validate_settings()
except ValueError as e:
    import logging
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical(f"CONFIGURATION ERROR: {e}")
    raise
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
