# =============================================================================
# Dockerfile - Asistente Andrea (Optimized Multi-Stage Build)
# =============================================================================
# Production-ready image with health checks and auto-migrations
# Compatible with Coolify deployment
# Punto A10: Non-root user for security
# =============================================================================

# =============================================================================
# Stage 1: Builder - Build dependencies and install packages
# =============================================================================
# =============================================================================
# Stage 1: Builder - Build dependencies and install packages
# =============================================================================
# FORCE AMD64: Azure Speech SDK only supports x86_64
FROM --platform=linux/amd64 python:3.11 as builder

WORKDIR /build

# Install build dependencies
# Start with 'fat' image but ensure Rust is present for Cryptography if needed
RUN apt-get update && apt-get install -y \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-core.txt requirements-minimal.txt requirements-prod.txt requirements.txt ./

# STAGED INSTALLATION - Identify failing package
# Stage 1: Core (FastAPI, Uvicorn) - Should NEVER fail
RUN echo "===== STAGE 1: Core packages =====" && \
    pip install --upgrade pip && \
    pip install --no-cache-dir --user --prefer-binary \
    fastapi~=0.128.0 \
    uvicorn[standard]~=0.40.0 \
    python-dotenv~=1.2.1 \
    pydantic-settings~=2.12.0 && \
    echo "✅ Stage 1 complete"

# Stage 2: Database
RUN echo "===== STAGE 2: Database packages =====" && \
    pip install --no-cache-dir --user --prefer-binary \
    sqlalchemy~=2.0.45 \
    asyncpg~=0.31.0 \
    alembic~=1.17.2 && \
    echo "✅ Stage 2 complete"

# Stage 3: Azure Speech (CRITICAL TEST)
RUN echo "===== STAGE 3: Azure Speech SDK =====" && \
    pip install --no-cache-dir --user --prefer-binary \
    azure-cognitiveservices-speech>=1.34.0 && \
    echo "✅ Stage 3 complete"

# Stage 4: Individual package installation with diagnostics
# Install EACH package separately to identify exact failure point

RUN echo "===== STAGE 4.1: HTTP Client (httpx) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary httpx~=0.28.1 && \
    echo "✅ httpx installed"

RUN echo "===== STAGE 4.2: Forms (python-multipart) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary python-multipart~=0.0.21 && \
    echo "✅ python-multipart installed"

RUN echo "===== STAGE 4.3: Templates (jinja2) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary jinja2~=3.1.6 && \
    echo "✅ jinja2 installed"

RUN echo "===== STAGE 4.4: Twilio SDK =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary twilio~=10.4.0 && \
    echo "✅ twilio installed"

RUN echo "===== STAGE 4.5: Rate Limiting (slowapi) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary slowapi~=0.1.9 && \
    echo "✅ slowapi installed"

RUN echo "===== STAGE 4.6: Security - Cryptography =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "cryptography>=42.0.0,<45.0.0" && \
    echo "✅ cryptography installed"

RUN echo "===== STAGE 4.7: Security - h11 =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "h11>=0.16.0" && \
    echo "✅ h11 installed"

RUN echo "===== STAGE 4.8: Security - urllib3 =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "urllib3>=2.6.3" && \
    echo "✅ urllib3 installed"

RUN echo "===== STAGE 4.9: Security - httpcore =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "httpcore>=1.0.9" && \
    echo "✅ httpcore installed"

RUN echo "===== STAGE 4.10: Input Sanitization (markupsafe) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary markupsafe~=2.1.5 && \
    echo "✅ markupsafe installed"

RUN echo "===== STAGE 4.11: Redis Client =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "redis[hiredis]~=5.0.1" && \
    echo "✅ redis installed"

RUN echo "===== STAGE 4.12: Audio Processing (NumPy) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "numpy>=1.26.0" && \
    echo "✅ numpy installed"

RUN echo "===== STAGE 4.13: Monitoring (prometheus-client) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary "prometheus-client>=0.20.0" && \
    echo "✅ prometheus-client installed"

RUN echo "===== STAGE 4.14: Logging (python-json-logger) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary python-json-logger~=2.0.7 && \
    echo "✅ python-json-logger installed"

RUN echo "===== STAGE 4.15: Correlation ID (asgi-correlation-id) =====" && \
    pip install -vv --no-cache-dir --user --prefer-binary asgi-correlation-id~=4.3.1 && \
    echo "✅ asgi-correlation-id installed"

RUN echo "✅✅✅ ALL STAGE 4 PACKAGES INSTALLED SUCCESSFULLY ✅✅✅"

# =============================================================================
# Stage 2: Runtime - Minimal production image
# =============================================================================
FROM --platform=linux/amd64 python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    libasound2 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    libuuid1 \
    tzdata \
    procps \
    && rm -rf /var/lib/apt/lists/*

LABEL maintainer="Martin Team <admin@voice-assistant.com>" \
    version="2.0" \
    description="Asistente Andrea Voice Orchestrator"

# =============================================================================
# Punto A10: Create non-root user for security
# =============================================================================
# Running as root is a security risk. Create 'app' user with UID 1000.
# This prevents privilege escalation and reduces attack surface.
# =============================================================================
RUN groupadd -r app --gid=1000 && \
    useradd -r -g app --uid=1000 --home-dir=/app --shell=/bin/bash app

# Copy Python packages from builder (to app user home)
COPY --from=builder --chown=app:app /root/.local /home/app/.local

# Copy application code with correct ownership
COPY --chown=app:app . .

# Make startup script executable
RUN chmod +x scripts/startup.sh

# Set environment
ENV PATH=/home/app/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Health check - calls /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# =============================================================================
# Punto A10: Switch to non-root user
# =============================================================================
# CRITICAL: This must be BEFORE CMD. Everything after this runs as 'app' user.
# =============================================================================
USER app

# Run startup script (includes migrations)
CMD ["./scripts/startup.sh"]
