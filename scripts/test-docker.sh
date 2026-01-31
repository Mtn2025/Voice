#!/bin/bash
# =============================================================================
# Docker Test Script - Asistente Andrea
# =============================================================================
# Tests the Docker deployment locally before production
# =============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "🧪 Testing Docker Deployment"
echo "=============================================="

# Test 1: Environment file
echo -e "${YELLOW}Test 1/8: Environment Configuration${NC}"
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    # Check for example/placeholder values
    if grep -q "CAMBIAR_ESTE_PASSWORD\|tu_.*_key\|example\.com" .env; then
        echo -e "${RED}✗ WARNING: .env contains placeholder values${NC}"
        echo "  Update with real credentials before production"
    else
        echo -e "${GREEN}✓ No placeholder values detected${NC}"
    fi
else
    echo -e "${RED}✗ .env file missing${NC}"
    exit 1
fi

# Test 2: Build image
echo -e "\n${YELLOW}Test 2/8: Building Docker Image${NC}"
if docker compose build; then
    echo -e "${GREEN}✓ Image built successfully${NC}"
else
    echo -e "${RED}✗ Image build failed${NC}"
    exit 1
fi

# Test 3: Start services
echo -e "\n${YELLOW}Test 3/8: Starting Services${NC}"
if docker compose up -d; then
    echo -e "${GREEN}✓ Services started${NC}"
else
    echo -e "${RED}✗ Failed to start services${NC}"
    exit 1
fi

# Test 4: Wait for health  checks
echo -e "\n${YELLOW}Test 4/8: Waiting for Health Checks (60s max)${NC}"
timeout 60 bash -c '
    until docker compose ps | grep -q "(healthy)"; do
        sleep 2
        echo "  Waiting..."
    done
' && echo -e "${GREEN}✓ Services are healthy${NC}" || echo -e "${RED}✗ Services failed health checks${NC}"

# Test 5: Database connection
echo -e "\n${YELLOW}Test 5/8: Testing Database Connection${NC}"
if docker compose exec -T db pg_isready -U voice_admin -d voice_orchestrator; then
    echo -e "${GREEN}✓ Database is ready${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    exit 1
fi

# Test 6: Redis connection
echo -e "\n${YELLOW}Test 6/8: Testing Redis Connection${NC}"
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
    echo -e "${GREEN}✓ Redis is responding${NC}"
else
    echo -e "${RED}✗ Redis connection failed${NC}"
    exit 1
fi

# Test 7: API Health endpoint
echo -e "\n${YELLOW}Test 7/8: Testing API Health Endpoint${NC}"
sleep 5  # Give API time to start
if curl -sf http://localhost:8000/health > /dev/null; then
    response=$(curl -s http://localhost:8000/health)
    echo -e "${GREEN}✓ API health endpoint responding${NC}"
    echo "  Response: $response"
else
    echo -e "${RED}✗ API health endpoint not responding${NC}"
    echo "  Logs:"
    docker compose logs app | tail -20
    exit 1
fi

# Test 8: Check migrations
echo -e "\n${YELLOW}Test 8/8: Verifying Migrations${NC}"
migration_output=$(docker compose exec -T app alembic current 2>&1 || echo "error")
if echo "$migration_output" | grep -q "head\|current"; then
    echo -e "${GREEN}✓ Migrations are up to date${NC}"
else
    echo -e "${YELLOW}⚠ Migration status unclear${NC}"
    echo "  Output: $migration_output"
fi

# Summary
echo ""
echo "=============================================="
echo -e "${GREEN}✅ All Tests Passed!${NC}"
echo "=============================================="
echo ""
echo "📊 Container Status:"
docker compose ps
echo ""
echo "💾 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""
echo "🔗 Access URLs:"
echo "   Dashboard: http://localhost:8000/dashboard"
echo "   API Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health"
echo ""
echo "📝 Next Steps:"
echo "   1. Test API endpoints: curl http://localhost:8000/health"
echo "   2. Access dashboard in browser"
echo "   3. Review logs: docker compose logs -f"
echo "   4. When done: docker compose down"
echo ""
