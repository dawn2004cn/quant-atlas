# Release Checklist

> Every release must pass through these gates before deployment.

## Pre-Release Gates

### Code Quality
- [ ] `ruff check app/ tests/` passes
- [ ] `ruff format --check app/ tests/` passes
- [ ] `pytest` passes (all suites)
- [ ] Coverage >= 60% threshold
- [ ] No P0/P1 security issues

### Deployment Readiness
- [ ] `Dockerfile` builds successfully: `docker build -t quant-atlas .`
- [ ] `docker compose up -d` starts all services
- [ ] Health checks pass: `/api/v1/health` returns 200
- [ ] Database migrations apply: `alembic upgrade head`
- [ ] Rollback tested: `alembic downgrade -1` succeeds

### Security
- [ ] No hardcoded secrets in code
- [ ] `FLASK_SECRET_KEY` is a strong random value
- [ ] `SOCKETIO_ALLOWED_ORIGINS` is set (not wildcard)
- [ ] HSTS header present in production response
- [ ] No `DEBUG=1` in production config

### Documentation
- [ ] `REFACTORING_LOG.md` updated with changes
- [ ] `DEPLOYMENT_GUIDE.md` is current
- [ ] `MIGRATION_GUIDE.md` covers new migrations
- [ ] Breaking API changes documented

### Testing
- [ ] Smoke tests pass: `pytest tests/smoke/ -v`
- [ ] Core API routes return 200
- [ ] Login/logout flow works
- [ ] Celery workers process tasks (if enabled)

## Deployment Steps

1. [ ] Notify team of deployment window
2. [ ] Create deployment branch: `git checkout -b release/vX.Y.Z`
3. [ ] Merge to main: `git checkout main && git merge release/vX.Y.Z`
4. [ ] Tag release: `git tag -a vX.Y.Z -m "Release vX.Y.Z"`
5. [ ] Push: `git push origin main --tags`
6. [ ] CI runs automatically — verify green
7. [ ] Deploy to staging
8. [ ] Run smoke tests on staging
9. [ ] Deploy to production
10. [ ] Monitor logs for 30 minutes
11. [ ] Take post-deploy backup

## Rollback Procedure

If issues detected:

1. [ ] Stop application: `docker compose stop web worker beat`
2. [ ] Switch to previous version: `git checkout vX.Y.Z-1`
3. [ ] Rebuild: `docker compose up -d --build`
4. [ ] Roll back migrations if needed: `alembic downgrade -1`
5. [ ] Verify health: `curl http://localhost:5000/api/v1/health`
6. [ ] Notify team of rollback
