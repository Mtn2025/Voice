# =============================================================================
# Deployment Guide - Asistente Andrea
# =============================================================================
# Complete guide for deploying to Coolify or other Docker environments
# =============================================================================

## Quick Start (Coolify)

### 1. Prerequisites
- Coolify instance running
- PostgreSQL database service created
- Domain configured (optional)

### 2. Deployment Steps

1. **Create Application in Coolify**
   - Type: Docker
   - Repository: Your Git repository
   - Branch: main

2. **Configure Environment Variables**
   
   Go to Coolify Dashboard → Your App → Environment Variables:
   
   ```
   # Azure Speech
   AZURE_SPEECH_KEY=your_key_here
   AZURE_SPEECH_REGION=eastus
   
   # Groq API
   GROQ_API_KEY=your_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   
   # Twilio (if using)
   TWILIO_ACCOUNT_SID=your_sid_here
   TWILIO_AUTH_TOKEN=your_token_here
   
   # Telnyx (if using)
   TELNYX_API_KEY=your_key_here
   
   # Database (auto-configured by Coolify)
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=secure_password_here
   POSTGRES_SERVER=postgres
   POSTGRES_PORT=5432
   POSTGRES_DB=voice_db
   
   # Auth
   ADMIN_API_KEY=generate_with_python_command
   ```

3. **Connect Database**
   - Link PostgreSQL service to application
   - Coolify auto-configures DATABASE_URL

4. **Deploy**
   - Click "Deploy" button
   - Monitor build logs
   - Wait for "✅ Deployment successful"

### 3. Post-Deployment Verification

```bash
# Check health
curl https://your-app.coolify.io/health

# Check dashboard (requires auth)
curl -H "X-API-Key: your_admin_key" https://your-app.coolify.io/dashboard
```

---

## Local Development (Docker)

### Using docker-compose

```bash
# 1. Copy environment file
cp .env.example .env

# 2. Fill .env with your credentials

# 3. Start services
docker-compose up -d

# 4. Check logs
docker-compose logs -f app

# 5. Access application
open http://localhost:8000/dashboard
```

### Manual Docker Build

```bash
# Build image
docker build -t asistente-andrea .

# Run container
docker run -d \
  --name asistente-andrea \
  -p 8000:8000 \
  --env-file .env \
  asistente-andrea

# View logs
docker logs -f asistente-andrea
```

---

## Database Migrations

Migrations run automatically on startup via `scripts/startup.sh`.

### Manual Migration

```bash
# Inside container
docker exec -it asistente-andrea bash
alembic upgrade head

# Or from host (with app running)
docker-compose exec app alembic upgrade head
```

### Rollback Migration

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade revision_id
```

### Check Migration Status

```bash
# Current version
alembic current

# Migration history
alembic history
```

---

## Health Checks

The application includes built-in health checks:

- **Endpoint:** `/health`
- **Interval:** Every 30s
- **Timeout:** 10s
- **Start Period:** 40s (allows startup time)
- **Retries:** 3 before marking unhealthy

```bash
# Manual health check
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

---

## Troubleshooting

### Database Connection Errors

```bash
# Check database is running
docker-compose ps

# Check DATABASE_URL
docker-compose exec app env | grep DATABASE_URL

# Test connection manually
docker-compose exec app python -c "
from app.db.database import engine
print('DB connection OK')
"
```

### Migration Failures

```bash
# View migration error details
docker-compose logs app | grep -A 10 "migration"

# Reset database (CAUTION: destroys data)
docker-compose down -v
docker-compose up -d
```

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 PID

# Or change port in docker-compose.yml
ports:
  - "8001:8000"  # Host:Container
```

### Permission Denied on startup.sh

```bash
# Make script executable
chmod +x scripts/startup.sh

# Rebuild image
docker-compose build
```

---

## Production Best Practices

### 1. Security

- ✅ Use strong passwords (>20 chars)
- ✅ Rotate API keys every 90 days
- ✅ Enable HTTPS (Coolify handles this)
- ✅ Use Coolify's "Secret" option for sensitive vars
- ✅ Enable 2FA on all service accounts
- ✅ Whitelist IPs for database access

### 2. Performance

- ✅ Use multi-stage Docker builds (already configured)
- ✅ Monitor memory usage (set limits if needed)
- ✅ Enable connection pooling (SQLAlchemy default)
- ✅ Set appropriate worker count (1 for voice apps)

### 3. Monitoring

- ✅ Check Coolify logs daily
- ✅ Set up health check alerts
- ✅ Monitor API usage quotas (Azure, Groq)
- ✅ Track database size growth
- ✅ Enable error reporting (e.g., Sentry)

### 4. Backups

```bash
# Backup database
docker-compose exec db pg_dump -U postgres voice_db > backup_$(date +%Y%m%d).sql

# Restore database
docker-compose exec -T db psql -U postgres voice_db < backup_20261231.sql
```

### 5. Scaling

Current setup:
- **Workers:** 1 (recommended for WebSocket stability)
- **Database:** Single instance (Coolify managed)
- **Scaling:** Vertical (increase container resources)

For horizontal scaling:
- Use load balancer with sticky sessions
- Shared Redis for session state
- Read replicas for database

---

## Environment-Specific Configs

### Development
```env
PYTHON_ENV=development
LOG_LEVEL=debug
AUTO_RELOAD=true
```

### Staging
```env
PYTHON_ENV=staging
LOG_LEVEL=info
AUTO_RELOAD=false
```

### Production
```env
PYTHON_ENV=production
LOG_LEVEL=warning
AUTO_RELOAD=false
```

---

## Useful Commands

```bash
# View all containers
docker-compose ps

# Restart application
docker-compose restart app

# View logs (last 100 lines)
docker-compose logs --tail=100 app

# Follow logs
docker-compose logs -f app

# Execute command in container
docker-compose exec app python -c "print('Hello')"

# Access container shell
docker-compose exec app bash

# Rebuild without cache
docker-compose build --no-cache

# Clean up everything
docker-compose down -v --remove-orphans
```

---

## Support

For deployment issues:
1. Check application logs
2. Verify environment variables
3. Test database connection
4. Review migration status
5. Check Coolify documentation: https://coolify.io/docs

---

**Last Updated:** 2026-01-06  
**Coolify Compatibility:** ✅ Tested  
**Docker Version:** 20.10+  
**Docker Compose Version:** 2.0+
