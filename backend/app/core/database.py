import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger(__name__)

# Normalize DATABASE_URL for SQLAlchemy with psycopg2
raw_url = settings.DATABASE_URL or ""
if raw_url.startswith("postgresql://"):
    db_url = raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
else:
    db_url = raw_url

# Remove channel_binding parameter if present as psycopg2 handles SSL natively
if "channel_binding=" in db_url:
    parts = db_url.split("?")
    base = parts[0]
    if len(parts) > 1:
        query_params = [p for p in parts[1].split("&") if not p.startswith("channel_binding=")]
        db_url = base + ("?" + "&".join(query_params) if query_params else "")

engine = create_engine(
    db_url,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initializes pgvector extension and creates all database tables."""
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            conn.commit()
            logger.info("pgvector extension verified on PostgreSQL.")
        
        # Import models so Base.metadata knows about them
        import app.models.schema  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info("All InSight database tables verified and created.")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False

def check_db_connection() -> dict:
    """Checks the database health and connectivity status."""
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT version();")).scalar()
            ext = conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'vector';")).scalar()
            return {
                "connected": True,
                "database_version": res,
                "pgvector_version": ext or "not installed",
                "pool_status": "healthy"
            }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "pool_status": "disconnected"
        }
