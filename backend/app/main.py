from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import register_exception_handlers
from app.core.database import init_db
from app.api.api_router import api_router
from app.api.v1.health import router as root_health_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup sequence
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.ENVIRONMENT}]")
    logger.info(f"Database dialect target: {settings.DATABASE_URL.split(':')[0]}")
    
    # Auto-initialize SQLite schema if in fallback / local dev mode
    if settings.DATABASE_URL.startswith("sqlite"):
        await init_db()

    yield

    # Teardown sequence
    logger.info(f"Shutting down {settings.APP_NAME} gracefully.")


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Comprehensive Statutory Regulatory Approval & Compliance Intelligence Platform for AICTE (SIH 2026 Problem Statement 26262)",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register centralized exception handling
    register_exception_handlers(app)

    # Mount /api/health and /api/ready at both /api and /api/v1
    app.include_router(root_health_router, prefix="/api")
    app.include_router(api_router, prefix=settings.API_PREFIX)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
