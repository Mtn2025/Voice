#!/bin/bash
# =============================================================================
# Docker Deployment Script - Asistente Andrea
# =============================================================================
# Usage: ./scripts/deploy.sh [environment]
# Environments: dev, staging, production
# =============================================================================

set -e  # Exit on error

ENVIRONMENT=${1:-dev}
ENV_FILE=".env"

echo "=============================================="
echo "🚀 Deploying Asistente Andrea"
echo "Environment: $ENVIRONMENT"
echo "=============================================="

# Validate environment file exists
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ Error: $ENV_FILE not found"
    echo "📝 Create it from template: cp .env.docker .env"
    exit 1
fi

# Validate required environment variables
echo "✅ Step 1/6: Validating environment variables..."
required_vars=(
    "POSTGRES_PASSWORD"
    "ADMIN_API_KEY"
    "AZURE_SPEECH_KEY"
    "GROQ_API_KEY"
)

for var in "${required_vars[@]}"; do
    if ! grep -q "^$var=" "$ENV_FILE"; then
        echo "❌ Missing required variable: $var"
        exit 1
    fi
done
echo "   ✓ All required variables present"

# Stop existing containers
echo "✅ Step 2/6: Stopping existing containers..."
docker compose down || true

# Build new image
echo "✅ Step 3/6: Building Docker image..."
docker compose build --no-cache

# Start services
echo "✅ Step 4/6: Starting services..."
docker compose up -d

# Wait for database
echo "✅ Step 5/6: Waiting for database..."
timeout 30 bash -c 'until docker compose exec -T db pg_isready -U ${POSTGRES_USER:-voice_admin}; do sleep 1; done'

# Run migrations
echo "✅ Step 6/6: Running database migrations..."
docker compose exec -T app alembic upgrade head

echo ""
echo "=============================================="
echo "✅ Deployment Complete!"
echo "=============================================="
echo ""
echo "📊 Service Status:"
docker compose ps

echo ""
echo "🔗 Access Points:"
echo "   API: http://localhost:8000"
echo "   Dashboard: http://localhost:8000/dashboard"
echo "   Health: http://localhost:8000/health"
echo "   Docs: http://localhost:8000/docs"
echo ""
echo "📝 Useful Commands:"
echo "   View logs:    docker compose logs -f app"
echo "   Stop:         docker compose down"
echo "   Restart:      docker compose restart"
echo "   Shell:        docker compose exec app bash"
echo ""
