import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_state import redis_state
from app.db.database import get_db

router = APIRouter()

@router.get("/health", tags=["System"], status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health Check Endpoint.
    Verifies connectivity to Database and Redis.
    Returns 200 OK if app is running, with component status details.
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }

    # 1. Check Database (Required)
    try:
        await db.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logging.error(f"Health Check DB Error: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"

    # 2. Check Redis (Optional/Fallback)
    try:
        if redis_state.is_redis_enabled and redis_state.redis:
             if await redis_state.redis.ping():
                health_status["redis"] = "connected"
             else:
                health_status["redis"] = "disconnected"
                health_status["status"] = "degraded"
        else:
             health_status["redis"] = "disabled"
    except Exception as e:
        logging.error(f"Health Check Redis Error: {e}")
        health_status["redis"] = "error"
        health_status["status"] = "degraded"

    return health_status
