# Docker Deployment Guide - Asistente Andrea

**Version**: 2.1  
**Last Updated**: 31 January 2026  
**Status**: Production-Ready ✅

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Local Testing](#local-testing)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Health](#monitoring--health)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

---

## Prerequisites

### Required Software

- **Docker**: 24.0+ (with Docker Compose V2)
- **Git**: For cloning the repository

### Required Credentials

Before deploying, you'll need API keys for:

1. **Azure Cognitive Services** (STT/TTS)
2. **Groq** (LLM - Primary)
3. **Telnyx** (Telephony)
4. **Admin API Key** (Dashboard access)

### System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| CPU | 2 cores | 4+ cores |
| RAM | 4 GB | 8+ GB |
| Disk | 10 GB | 20+ GB SSD |
| Network | 10 Mbps | 100+ Mbps |

---

## Quick Start

### 1. Clone Repository

```bash
git clone <repository-url>
cd asistente-andrea
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.docker .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### 3. Deploy

```bash
# Option A: Using deployment script (Recommended)
chmod +x scripts/deploy.sh
./scripts/deploy.sh

# Option B: Manual deployment
docker compose build
docker compose up -d
```

### 4. Verify

```bash
# Check service status
docker compose ps

# Test health endpoint
curl http://localhost:8000/health

# Access dashboard
# Open browser: http://localhost:8000/dashboard
```

---

## Configuration

### Environment Variables (.env)

#### Core Database

```ini
POSTGRES_USER=voice_admin
POSTGRES_PASSWORD=<generate-secure-password>
POSTGRES_DB=voice_orchestrator
POSTGRES_SERVER=db
POSTGRES_PORT=5432
```

**Generate secure password:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Security

```ini
ADMIN_API_KEY=<your-secret-key>
```

#### AI Providers

```ini
# Azure (STT/TTS)
AZURE_SPEECH_KEY=<your-azure-key>
AZURE_SPEECH_REGION=eastus

# Groq (LLM)
GROQ_API_KEY=gsk_<your-groq-key>

# Azure OpenAI (Optional)
AZURE_OPENAI_KEY=<your-key>
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
```

#### Telephony

```ini
TELNYX_API_KEY=<your-telnyx-key>
TELNYX_CONNECTION_ID=<your-connection-id>
```

#### Application

```ini
ENVIRONMENT=production
LOG_LEVEL=INFO
DEBUG=false
ALLOWED_ORIGINS=https://yourdomain.com
```

### Docker Compose Services

The stack includes 3 services:

1. **app**: FastAPI application (Port 8000)
2. **db**: PostgreSQL 15 database
3. **redis**: Redis 7 cache

All services include health checks and automatic restart.

---

## Local Testing

### Using Test Script

```bash
chmod +x scripts/test-docker.sh
./scripts/test-docker.sh
```

The test script verifies:

- ✅ Environment configuration
- ✅ Docker image build
- ✅ Service startup
- ✅ Health checks
- ✅ Database connectivity
- ✅ Redis connectivity
- ✅ API endpoints
- ✅ Database migrations

### Manual Testing

```bash
# 1. Build and start
docker compose up -d

# 2. Watch logs
docker compose logs -f

# 3. Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"2.1","database":"connected"}

# 4. Test API docs
curl http://localhost:8000/docs
# Opens in browser: Swagger UI

# 5. Check migrations
docker compose exec app alembic current

# 6. Access dashboard
# Browser: http://localhost:8000/dashboard
# Login with: ADMIN_API_KEY from .env
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] ✅ .env file configured with PRODUCTION credentials
- [ ] ✅ POSTGRES_PASSWORD is strong (32+ characters)
- [ ] ✅ ADMIN_API_KEY is unique and secure
- [ ] ✅ All API keys are valid and tested
- [ ] ✅ ALLOWED_ORIGINS set to production domains
- [ ] ✅ DEBUG=false
- [ ] ✅ LOG_LEVEL=INFO or WARNING
- [ ] ✅ SSL/TLS certificates configured (if applicable)
- [ ] ✅ Firewall rules configured
- [ ] ✅ Backup strategy defined

### Deployment Steps

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Deploy Application

```bash
# Clone repository
git clone <repository-url>
cd asistente-andrea

# Configure environment
cp .env.docker .env
# IMPORTANT: Edit .env with production credentials

# Deploy
chmod +x scripts/deploy.sh
./scripts/deploy.sh production
```

#### 3. Configure Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/voice-orchestrator

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert. pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/voice-orchestrator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### 4. Configure Firewall

```bash
# UFW example
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

---

## Monitoring & Health

### Health Checks

```bash
# Application health
curl https://yourdomain.com/health

# Expected response:
{
  "status": "healthy",
  "version": "2.1",
  "database": "connected",
  "redis": "connected",
  "uptime_seconds": 3600
}
```

### Docker Health Status

```bash
# Service status
docker compose ps

# Should show all services as "healthy"
```

### Logging

```bash
# View all logs
docker compose logs

# Follow app logs
docker compose logs -f app

# Last 100 lines
docker compose logs --tail=100 app

# Filter by timestamp
docker compose logs --since 1h app
```

### Resource Monitoring

```bash
# Container stats
docker stats

# Detailed resource usage
docker compose top
```

### Database Monitoring

```bash
# Connect to database
docker compose exec db psql -U voice_admin -d voice_orchestrator

# Check connections
SELECT count(*) FROM pg_stat_activity;

# Table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker compose logs app

# Common issues:
# 1. Missing environment variables
# 2. Database not ready
# 3. Port already in use
```

**Solution for port conflict:**
```bash
# Find process using port 8000
sudo lsof -i :8000
# Kill it or change port in docker-compose.yml
```

### Database Connection Failed

```bash
# Check if database is running
docker compose ps db

# Should show "healthy"

# Test connection manually
docker compose exec db pg_isready -U voice_admin -d voice_orchestrator

# Check logs
docker compose logs db
```

**Common causes:**
- POSTGRES_PASSWORD mismatch
- Database not fully initialized
- Network issues between containers

### Migration Errors

```bash
# Check current migration
docker compose exec app alembic current

# View migration history
docker compose exec app alembic history

# Force upgrade
docker compose exec app alembic upgrade head

# If stuck, downgrade and re-upgrade
docker compose exec app alembic downgrade -1
docker compose exec app alembic upgrade head
```

### API Not Responding

```bash
# Check if app container is running
docker compose ps app

# Check logs for errors
docker compose logs app | grep -i error

# Restart app container
docker compose restart app

# Full restart
docker compose down
docker compose up -d
```

### High Memory Usage

```bash
# Check memory stats
docker stats --no-stream

# If app using too much memory:
# 1. Check for memory leaks in logs
# 2. Restart container
docker compose restart app

# Permanent fix: Add memory limits to docker-compose.yml
# services:
#   app:
#     mem_limit: 2g
#     mem_reservation: 1g
```

### SSL/HTTPS Issues

```bash
# Verify certificate
openssl s_client -connect yourdomain.com:443

# Check Nginx config
sudo nginx -t

# View  Nginx logs
sudo tail -f /var/log/nginx/error.log
```

---

## Security Best Practices

### 1. Environment Variables

✅ **DO:**
- Use strong, randomly generated passwords (32+ characters)
- Rotate credentials every 90 days
- Use secrets management (AWS Secrets, HashiCorp Vault)
- Set `.env` permissions: `chmod 600 .env`

❌ **DON'T:**
- Commit `.env` to Git
- Use default passwords
- Share credentials via email/Slack
- Hardcode credentials in docker-compose.yml

### 2. Network Security

✅ **DO:**
- Use HTTPS only (no plain HTTP)
- Configure firewall (UFW/iptables)
- Use VPN for database access
- Implement rate limiting

❌ **DON'T:**
- Expose database ports publicly
- Allow SSH root login
- Use weak SSL/TLS ciphers

### 3. Application Security

✅ **DO:**
- Run as non-root user (already configured)
- Keep dependencies updated
- Enable audit logging
- Use CSRF protection

❌ **DON'T:**
- Run DEBUG=true in production
- Disable security headers
- Expose internal errors to users

### 4. Backup Strategy

```bash
# Automated database backup script
#!/bin/bash
BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

docker compose exec -T db pg_dump \
    -U voice_admin \
    -d voice_orchestrator \
    > $BACKUP_DIR/backup_$DATE.sql

# Compress
gzip $BACKUP_DIR/backup_$DATE.sql

# Keep only last 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

Add to cron tab:
```bash
crontab -e
# Daily backup at 2 AM
0 2 * * * /path/to/backup-script.sh
```

### 5. Update Strategy

```bash
# 1. Backup first
./scripts/backup.sh

# 2. Pull latest code
git pull origin main

# 3. Rebuild with no cache
docker compose build --no-cache

# 4. Apply migrations
docker compose up -d
docker compose exec app alembic upgrade head

# 5. Verify
curl https://yourdomain.com/health
```

---

## Additional Resources

- **Architecture**: See `ARCHITECTURE.md`
- **Database**: See `docs/DATABASE_INTERNAL_FIELDS.md`
- **API Docs**: `https://yourdomain.com/docs`
- **Status Report**: `docs/STATUS_REPORT_2026-01-31.md`

---

## Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Review troubleshooting section
3. Contact: admin@voice-orchestrator.com

---

**Last Updated**: 31 January 2026  
**Version**: 2.1  
**Status**: Production-Ready ✅
