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
    
    # Neon / Azure PostgreSQL connection string
    DATABASE_URL: Optional[str] = "postgresql://neondb_owner:npg_6adiITkSX0ML@ep-bold-glitter-b324brx0-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
    USE_DB_STORAGE: bool = True
    
    # Vector Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # Neon Auth (Better Auth) URLs
    NEON_AUTH_URL: str = "https://ep-bold-glitter-b324brx0.neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth"
    NEON_JWKS_URL: str = "https://ep-bold-glitter-b324brx0.neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth/.well-known/jwks.json"

    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
