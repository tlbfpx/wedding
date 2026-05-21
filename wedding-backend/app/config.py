from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+asyncmy://root:123456@localhost:3306/wedding"
    REDIS_URL: str = "redis://localhost:6379/0"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10
    APP_NAME: str = "婚庆管理系统"
    DEBUG: bool = True

    model_config = {"env_file": ".env"}


settings = Settings()
Path(settings.UPLOAD_DIR).mkdir(exist_ok=True)
