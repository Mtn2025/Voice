#!/bin/bash
# =============================================================================
# Startup Script for Asistente Andrea
# =============================================================================
# This script runs on container startup (Coolify/Docker)
# Executes database migrations and starts the application
# =============================================================================

set -e  # Exit on error

echo "🚀 Starting Asistente Andrea..."

# =============================================================================
# 1. Wait for Database to be ready
# =============================================================================
echo "📦 Waiting for PostgreSQL..."
python -c "
import time
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

async def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    for i in range(max_retries):
        try:
            engine = create_async_engine(settings.DATABASE_URL)
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            await engine.dispose()
            print(f'✅ Database ready after {i+1} attempts')
            return True
        except Exception as e:
            if i < max_retries - 1:
                print(f'⏳ Database not ready, retry {i+1}/{max_retries}...')
                time.sleep(retry_interval)
            else:
                print(f'❌ Database connection failed after {max_retries} attempts')
                raise

asyncio.run(wait_for_db())
"

# =============================================================================
# 2. Run Database Migrations (Alembic)
# =============================================================================
echo "🔄 Running database migrations..."
alembic upgrade head || {
    echo "⚠️  Migrations failed, but continuing (tables might already exist)"
}

# =============================================================================
# 2.1 Run Manual Patches (Fases 7, 8, 9) - TEMPORARY FIX
# =============================================================================
echo "🛠️ Applying manual patches (CRM, Webhook, VAD)..."
echo "🛠️ Applying manual patches (CRM, Webhook, VAD)..."
# Environment vars are injected by Coolify/Docker. Do not override locally. 

python scripts/add_baserow_columns.py
python scripts/add_webhook_columns.py
python scripts/add_vad_columns.py

# =============================================================================
# 2.2 Compile CSS (Vite + Tailwind)
# =============================================================================
echo "🎨 Compiling Tailwind CSS via Vite..."
npm run build || echo "⚠️ CSS Build failed"

# =============================================================================
# 2.2 Verify/Download Models (Phase 1)
# =============================================================================
echo "🧠 Verifying AI Models..."
python scripts/download_model.py || echo "⚠️ Model download failed"

# =============================================================================
# 3. Start Application
# =============================================================================
echo "✅ Starting FastAPI application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
