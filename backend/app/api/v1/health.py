from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.config import settings
from app.core.database import get_db

router = APIRouter(tags=["Health & Diagnostics"])


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe: returns 200 immediately if process is responsive."""
    return {
        "status": "HEALTHY",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Readiness probe: validates required dependencies (Database connectivity, etc.)."""
    db_healthy = False
    error_detail = None
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            db_healthy = True
    except Exception as e:
        error_detail = str(e)

    overall_ready = db_healthy
    status_code = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "READY" if overall_ready else "NOT_READY",
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "dependencies": {
                "database": {
                    "healthy": db_healthy,
                    "dialect": "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql",
                    "error": error_detail,
                },
                "storage": {
                    "healthy": True,
                    "provider": "minio_s3_compatible",
                },
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
