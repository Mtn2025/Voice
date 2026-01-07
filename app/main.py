from contextlib import asynccontextmanager

# Punto B1: Logging Centralizado & Tracing
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import routes
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.routers import dashboard, system

# =============================================================================
# RATE LIMITING - Punto A3 del Plan Consolidado
# =============================================================================
# SlowAPI para protección contra DoS y control de costos
# Configuración: Por IP, almacenamiento en memoria (in-memory)
# =============================================================================
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # =============================================================================
    # Punto B1: Configure Structured Logging
    # =============================================================================
    configure_logging()
    # =============================================================================

    # Load resources
    from app.core.secure_logging import get_secure_logger
    logger = get_secure_logger(__name__)
    logger.info("Starting Voice Orchestrator...")

    # Configuration status (secure - no keys exposed)
    logger.info(f"Telnyx API configured: {bool(settings.TELNYX_API_KEY)}")
    logger.info(f"Azure Speech configured: {bool(settings.AZURE_SPEECH_KEY)}")
    logger.info(f"Groq API configured: {bool(settings.GROQ_API_KEY)}")

    # =============================================================================
    # Punto A9: Initialize Redis for Horizontal Scaling
    # =============================================================================
    from app.core.http_client import http_client
    from app.core.redis_state import redis_state
    await redis_state.connect()
    if redis_state.is_redis_enabled:
        logger.info("✅ [A9] Redis state management enabled - Multi-instance ready")
    else:
        logger.warning("⚠️ [A9] Redis unavailable - Using in-memory fallback (single instance only)")

    # Initialize HTTP Client (Punto C3)
    await http_client.init()
    logger.info("✅ [HTTP] Global HTTP Client Initialized")
    # =============================================================================

    # Run database migrations with Alembic
    from alembic import command
    from alembic.config import Config
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        # Continue anyway - tables might already exist

    # Init DB Tables (create_all for safety, Alembic handles schema)
    from app.db.database import engine
    from app.db.models import Base
    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ Application startup complete")

    yield  # App is running

    # Cleanup on shutdown
    logger.info("Shutting down Voice Orchestrator...")

    # =============================================================================
    # Punto A9: Close Redis Connection
    # =============================================================================
    await redis_state.disconnect()
    logger.info("✅ [A9] Redis disconnected")

    await http_client.close()
    logger.info("✅ [HTTP] Global HTTP Client Closed")
    # =============================================================================

    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title="Voice Orchestrator Agent",
    description="AI Voice Assistant with Telnyx, Azure, and Groq integration",
    version="1.0.0",
    lifespan=lifespan
)

# Punto B1: Add Request Tracing Middleware
# Must be added before other middlewares/routers
app.add_middleware(CorrelationIdMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Rate Limiting (Punto A3)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(routes.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router)
app.include_router(system.router)


from fastapi.responses import RedirectResponse


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")

@app.post("/", include_in_schema=False)
async def root_post():
    """
    Handle POST requests to root (e.g., from health checks or misconfigured webhooks).
    Returns 200 OK to prevent 405 errors flowing into logs.
    """
    return {"status": "ok", "message": "Voice Orchestrator Running"}


