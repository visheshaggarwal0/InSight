import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "InSight Telemetry Intelligence"
    VERSION: str = "2.0.0"
    API_V1_PREFIX: str = "/api"
    DEFAULT_DATASET: str = "d2c_cosmetics"
    
    # Neon / Azure PostgreSQL connection string (sourced from .env, defaults to local SQLite)
    DATABASE_URL: Optional[str] = "sqlite:///./insight_dev.db"
    USE_DB_STORAGE: bool = True
    
    # Vector Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Neon Auth (Better Auth) URLs
    NEON_AUTH_URL: Optional[str] = None
    NEON_JWKS_URL: Optional[str] = None

    # CORS Allowed Origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
