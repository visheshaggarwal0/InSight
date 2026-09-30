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

    # Deployment environment. Development enables localhost-only conveniences
    # (regex CORS, auto-reload) that must never apply in production.
    ENVIRONMENT: str = "development"

    # When true, every /api data route requires an authenticated caller.
    # Development defaults to false so the dashboard works without an auth
    # server; set REQUIRE_AUTH=true in any shared or deployed environment.
    REQUIRE_AUTH: bool = False

    # Localhost origins are matched by regex so any Vite dev port works.
    # Only honoured when ENVIRONMENT == "development".
    LOCALHOST_ORIGIN_REGEX: Optional[str] = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # Hard ceiling on uploaded CSV payloads (bytes). Prevents memory-exhaustion
    # DoS via `await file.read()` on an unbounded multipart body.
    MAX_UPLOAD_BYTES: int = 25 * 1024 * 1024
    MAX_UPLOAD_ROWS: int = 50_000

    # Minimum rows / distinct classes required before a supervised model is fitted.
    MIN_TRAIN_ROWS: int = 20

    # Roles permitted to request unredacted ("raw") customer text.
    PII_UNMASK_ROLES: list[str] = ["admin", "auditor", "compliance"]

    # HMAC key for the reversible PII surrogate vault. When unset, redaction
    # emits non-reversible placeholders (no surrogate tag).
    PII_VAULT_SECRET: Optional[str] = None

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
