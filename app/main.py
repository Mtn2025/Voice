import subprocess
import time
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles as BaseStaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.sessions import SessionMiddleware

from app.api import routes_v2
from app.core.config import settings
from app.core.http_client import http_client
from app.core.logging_config import configure_logging
from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_in_progress,
    http_requests_total,
)
from app.core.redis_state import redis_state
from app.core.secure_logging import get_secure_logger
from app.core.security_middleware import CSRFProtectionMiddleware, SecurityHeadersMiddleware
from app.db.database import engine
from app.db.models import Base
from app.routers import config_router, dashboard, history_router, system


# Disable Cache for Static Files
class StaticFiles(BaseStaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


# Rate Limiting Configuration
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Configure Logging
    configure_logging()
    logger = get_secure_logger(__name__)
    logger.info("Starting Voice Orchestrator...")

    # Log Configuration Status (Secure)
    logger.info(f"Telnyx API configured: {bool(settings.TELNYX_API_KEY)}")
    logger.info(f"Azure Speech configured: {bool(settings.AZURE_SPEECH_KEY)}")
    logger.info(f"Groq API configured: {bool(settings.GROQ_API_KEY)}")

    # 2. Initialize Redis
    await redis_state.connect()
    if redis_state.is_redis_enabled:
        logger.info("✅ Redis state management enabled")
    else:
        logger.warning("⚠️ Redis unavailable - Using in-memory fallback")

    # 3. Initialize HTTP Client
    await http_client.init()
    logger.info("✅ Global HTTP Client Initialized")

    # 4. Run Database Migrations
    try:
        db_url_safe = settings.DATABASE_URL.split("@")[-1]
        logger.info(f"🔌 Connecting to Database at: ...@{db_url_safe}")
        logger.info("Running database migrations...")

        # Run alembic in a separate process
        result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.error(f"Migration failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Error running migrations: {e}")

    # 5. Init DB Tables (Safety Check)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✅ Application startup complete")

    yield  # App is running

    # Shutdown Sequence
    logger.info("Shutting down Voice Orchestrator...")

    await redis_state.disconnect()
    logger.info("✅ Redis disconnected")

    await http_client.close()
    logger.info("✅ Global HTTP Client Closed")

    logger.info("✅ Application shutdown complete")


app = FastAPI(
    title="Voice Orchestrator Agent",
    description="AI Voice Assistant with Telnyx, Azure, and Groq integration",
    version="1.0.0",
    lifespan=lifespan
)

# Request Tracing
app.add_middleware(CorrelationIdMiddleware)

# Security Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CSRFProtectionMiddleware)

# Session Middleware (Must wrap CSRF)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SESSION_SECRET_KEY if hasattr(settings, 'SESSION_SECRET_KEY') else settings.ADMIN_API_KEY,
    max_age=3600,
    same_site="strict",
    https_only=False  # Set to True in production
)

# Metrics Middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Record HTTP metrics for monitoring."""
    method = request.method
    path = request.url.path

    if path == "/metrics":
        return await call_next(request)

    http_requests_in_progress.labels(method=method, path=path).inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.time() - start_time
        http_request_duration_seconds.labels(method=method, path=path).observe(duration)
        http_requests_total.labels(method=method, path=path, status_code=status_code).inc()
        http_requests_in_progress.labels(method=method, path=path).dec()

    return response


# Mount Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Rate Limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routes
app.include_router(routes_v2.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router)
app.include_router(system.router)
app.include_router(config_router.router)
app.include_router(history_router.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/dashboard")


@app.post("/", include_in_schema=False)
async def root_post():
    """Handle POST requests to root (prevent 405 errors from webhooks)."""
    return {"status": "ok", "message": "Voice Orchestrator Running"}
