from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.core.config import settings
from app.core.database import init_db, check_db_connection

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables and pgvector on startup
    init_db()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise Product & Telemetry Review Intelligence Backend",
    lifespan=lifespan
)

# Cross-Origin Resource Sharing (CORS) configured with specific origins and regex for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response

app.include_router(router, prefix=settings.API_V1_PREFIX)

@app.get("/")
def root():
    return {
        "service": settings.PROJECT_NAME,
        "status": "healthy",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    db_status = check_db_connection()
    return {
        "status": "ok",
        "database": db_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
