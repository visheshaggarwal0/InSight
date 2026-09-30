from contextlib import asynccontextmanager
import json

from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.database import init_db, check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and pgvector on startup.
    # The result is recorded so /health does not report "ok" while the DB is down.
    app.state.db_ready = bool(init_db())
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Product & Telemetry Review Intelligence Backend",
    lifespan=lifespan,
)

# Cross-Origin Resource Sharing.
# In production only the explicit allowlist is honoured. The localhost regex is
# a development convenience and is disabled outside development so a
# permissive dev posture cannot ship to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=(settings.LOCALHOST_ORIGIN_REGEX if settings.ENVIRONMENT == "development" else None),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=600,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "frame-ancestors 'none'"
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "version": settings.VERSION,
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    """
    Liveness/readiness probe.

    Reports "degraded" with HTTP 503 when the database is unreachable so an
    orchestrator can act on it, instead of unconditionally claiming "ok".
    """
    db_status = check_db_connection()
    healthy = bool(db_status.get("connected"))
    payload = {
        "status": "ok" if healthy else "degraded",
        "database": db_status,
    }
    if not healthy:
        return Response(
            content=json.dumps(payload),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )
    return payload


if __name__ == "__main__":
    import uvicorn

    # Local development only: bind to loopback with the reloader.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
