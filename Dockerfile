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
# FORCE AMD64: Azure Speech SDK only supports x86_64, fails on ARM (Apple Silicon/Graviton)
FROM --platform=linux/amd64 python:3.11-slim as builder

WORKDIR /build

# Install build dependencies (incl. Rust for cryptography/pydantic if wheels miss)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libssl-dev \
    libffi-dev \
    pkg-config \
    libasound2-dev \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    # Strategy: Install heavy binaries first with --prefer-binary to avoid compilation
    pip install --no-cache-dir --user --prefer-binary azure-cognitiveservices-speech>=1.34.0 && \
    # Install the rest
    pip install --no-cache-dir --user --prefer-binary -r requirements.txt

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
