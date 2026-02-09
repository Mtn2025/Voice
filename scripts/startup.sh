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
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def wait_for_db():
    max_retries = 30
    retry_interval = 2
    
    # Print diagnostic info
    db_url = settings.DATABASE_URL
    safe_url = db_url.split('@')[-1] if '@' in db_url else 'UNKNOWN'
    print(f'🔌 Connecting to database at: {safe_url}')
    print(f'📊 Server: {settings.POSTGRES_SERVER}')
    print(f'📊 Port: {settings.POSTGRES_PORT}')
    print(f'📊 Database: {settings.POSTGRES_DB}')
    print(f'📊 User: {settings.POSTGRES_USER}')
    
    for i in range(max_retries):
        try:
            engine = create_async_engine(settings.DATABASE_URL, echo=False)
            async with engine.connect() as conn:
                await conn.execute(text('SELECT 1'))
            await engine.dispose()
            print(f'✅ Database ready after {i+1} attempts')
            return True
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            if i < max_retries - 1:
                print(f'⏳ Retry {i+1}/{max_retries}: {error_type} - {error_msg[:100]}')
                time.sleep(retry_interval)
            else:
                print(f'❌ Database connection failed after {max_retries} attempts')
                print(f'❌ Last error: {error_type}')
                print(f'❌ Details: {error_msg}')
                print(f'')
                print(f'💡 Troubleshooting:')
                print(f'   - Check if PostgreSQL container is running')
                print(f'   - Verify POSTGRES_SERVER={settings.POSTGRES_SERVER} is correct')
                print(f'   - Check docker-compose depends_on healthcheck')
                print(f'   - Ensure database credentials are correct')
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
# 2.1 Compile CSS (Vite + Tailwind)
# =============================================================================
echo "🎨 Compiling Tailwind CSS via Vite..."
npm run build || echo "⚠️ CSS Build failed (non-critical)"

# =============================================================================
# 2.2 Verify/Download Models (Optional)
# =============================================================================
echo "🧠 Verifying AI Models..."
python scripts/download_model.py || echo "⚠️ Model download failed (non-critical)"

# =============================================================================
# 3. Start Application
# =============================================================================
echo "✅ Starting FastAPI application..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
