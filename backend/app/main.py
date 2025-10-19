"""
Main FastAPI application entry point.
Configures the app, middleware, and routes.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
from sqlalchemy import text

from app.config import settings
from app.database import engine, Base
from app.routers import auth, documents, query, rag, cache, users
from app.schemas import HealthResponse
from app.redis_client import get_redis

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="Internal Knowledge + Query Center with multi-modal RAG",
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,  # Disable docs in production
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(documents.router)
app.include_router(query.router)
app.include_router(rag.router)
app.include_router(cache.router)


@app.on_event("startup")
async def startup_event():
    """
    Application startup event.
    Initializes database tables and connections.
    """
    logger.info("Starting DocQuery application...")

    # Create database tables if they don't exist
    # In production, use Alembic migrations instead
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")

    # Test Redis connection
    try:
        redis = get_redis()
        redis.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")

    logger.info(f"DocQuery {settings.app_version} started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event.
    Cleanup and close connections.
    """
    logger.info("Shutting down DocQuery application...")


@app.get("/", tags=["Root"])
def read_root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs" if settings.debug else "disabled",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        Service health status including database and Redis connectivity
    """
    # Check database connection
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    # Check Redis connection
    try:
        redis = get_redis()
        redis.ping()
        redis_status = "connected"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        redis_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        database=db_status,
        redis=redis_status
    )
