# Deployment Guide

> End-to-end deployment instructions for Quant Atlas.

## Prerequisites

- Python 3.10+
- MySQL 8.0 (or SQLite for dev)
- Redis 7+ (optional, required for Celery)
- Docker & Docker Compose (optional, for containerized deployment)

## Option 1: Docker Compose (Recommended)

### Quick Start

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your values
# At minimum: FLASK_SECRET_KEY, MYSQL_PASSWORD

# Start all services
docker compose up -d

# Check health
docker compose ps

# View logs
docker compose logs -f web
```

### Services

| Service | Port | Purpose |
|---------|------|---------|
| web | 5000 | Flask application |
| worker | — | Celery task worker |
| beat | — | Celery scheduler |
| redis | 6379 | Cache & task broker |
| mysql | 3306 | Database |

### Stop

```bash
docker compose down          # stop without data
docker compose down -v       # stop and remove volumes
```

### Update

```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build
```

## Option 2: Bare Metal / VM

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set FLASK_SECRET_KEY, database credentials, etc.
```

### 3. Initialize database

```bash
# Run Alembic migrations
alembic upgrade head
```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for details.

### 4. Start the application

#### Development

```bash
python run.py
```

#### Production (with gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()" --timeout 120
```

#### Start Celery worker

```bash
celery -A app.celery_app.celery_app worker --loglevel=info
```

#### Start Celery beat

```bash
celery -A app.celery_app.celery_app beat --loglevel=info
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FLASK_SECRET_KEY` | Yes | — | Application secret key (generate with `openssl rand -hex 32`) |
| `DATABASE_BACKEND` | No | `sqlite` | `mysql`, `postgres`, `sqlite` |
| `MYSQL_HOST` | No | `127.0.0.1` | MySQL host |
| `MYSQL_PORT` | No | `3306` | MySQL port |
| `MYSQL_USER` | No | `quant_user` | MySQL user |
| `MYSQL_PASSWORD` | No | — | MySQL password |
| `MYSQL_DATABASE` | No | `quant_atlas` | MySQL database name |
| `REDIS_HOST` | No | `127.0.0.1` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `CELERY_BROKER_URL` | No | `redis://192.168.8.103:6380/0` | Celery broker URL |
| `ENABLE_CELERY` | No | `0` | Enable Celery |
| `ENABLE_QLIB` | No | `0` | Enable Qlib |
| `FLASK_DEBUG` | No | `0` | Enable debug mode |
| `SOCKETIO_ALLOWED_ORIGINS` | No | — | Comma-separated allowed CORS origins |

See `.env.example` for the full list.

## Health Checks

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/health` | GET | Service health status |
| `/system/health` | GET | System-level health |

Docker health check is built into `Dockerfile` — it probes `/system/health` every 30 seconds.

## Database Migrations

```bash
# Check current revision
alembic current

# Apply pending migrations
alembic upgrade head

# Roll back one step
alembic downgrade -1
```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for full details.

## Backup

```bash
# Full MySQL backup
mysqldump -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD \
  $MYSQL_DATABASE --single-transaction | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE < backup.sql
```

See [BACKUP_RESTORE.md](BACKUP_RESTORE.md) for full procedures.

## Logging

- Application logs: `logs/app.log`
- Docker logs: `docker compose logs -f`
- Rotate logs in production with `logrotate`

## Rollback

### Application rollback

```bash
# 1. Stop the current version
docker compose stop web

# 2. Checkout previous version
git checkout <previous-commit>

# 3. Rebuild and start
docker compose up -d --build web

# 4. Verify
curl http://localhost:5000/api/v1/health
```

### Database rollback

```bash
# Roll back to previous migration
alembic downgrade <previous-revision>
```

See [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) for caution notes.

## Troubleshooting

### App won't start

```bash
# Check logs
docker compose logs web
tail -f logs/app.log

# Test database connectivity
python -c "from app.config.settings import get_settings; print(get_settings().database_uri)"

# Test Redis connectivity
redis-cli -h $REDIS_HOST -p $REDIS_PORT ping
```

### Migration fails

```bash
# Check current state
alembic current

# Check available migrations
alembic history --verbose

# See the failing migration
cat alembic/versions/<revision_*.py>
```

### Health check returns 503

```bash
# Check individual services
docker compose ps
docker compose logs redis
docker compose logs mysql
```
