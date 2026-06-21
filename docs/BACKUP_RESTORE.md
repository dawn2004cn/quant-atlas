# Backup and Restore Procedures

> Protects against data loss from accidental deletion, corruption, or failed migrations.

## MySQL Database

### Backup

#### Full backup

```bash
mysqldump \
  -h ${MYSQL_HOST:-127.0.0.1} \
  -P ${MYSQL_PORT:-3306} \
  -u ${MYSQL_USER:-quant_user} \
  -p${MYSQL_PASSWORD} \
  ${MYSQL_DATABASE:-quant_atlas} \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  > quant_atlas_backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Compressed backup

```bash
mysqldump \
  -h ${MYSQL_HOST:-127.0.0.1} \
  -P ${MYSQL_PORT:-3306} \
  -u ${MYSQL_USER:-quant_user} \
  -p${MYSQL_PASSWORD} \
  ${MYSQL_DATABASE:-quant_atlas} \
  --single-transaction \
  | gzip > quant_atlas_backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### Restore

```bash
mysql \
  -h ${MYSQL_HOST:-127.0.0.1} \
  -P ${MYSQL_PORT:-3306} \
  -u ${MYSQL_USER:-quant_user} \
  -p${MYSQL_PASSWORD} \
  ${MYSQL_DATABASE:-quant_atlas} \
  < quant_atlas_backup_YYYYMMDD_HHMMSS.sql
```

### Automated daily backup (Linux cron)

```bash
# Add to crontab: crontab -e
# Daily at 2:00 AM
0 2 * * * /path/to/scripts/backup_db.sh
```

Create `scripts/backup_db.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/opt/quant-atlas/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

mysqldump \
  -h "${MYSQL_HOST:-127.0.0.1}" \
  -P "${MYSQL_PORT:-3306}" \
  -u "${MYSQL_USER:-quant_user}" \
  -p"${MYSQL_PASSWORD}" \
  "${MYSQL_DATABASE:-quant_atlas}" \
  --single-transaction \
  --routines \
  --triggers \
  | gzip > "$BACKUP_DIR/quant_atlas_${TIMESTAMP}.sql.gz"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "quant_atlas_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: quant_atlas_${TIMESTAMP}.sql.gz"
```

## SQLite Database

### Backup

```bash
# Copy the database file (preferred for SQLite — avoids LOCK issues)
cp instance/app_state_sqlite.db instance/app_state_sqlite.db.bak.$(date +%Y%m%d)
```

Or use `.backup` command:

```bash
sqlite3 instance/app_state_sqlite.db ".backup '/opt/quant-atlas/backups/app_state_sqlite.db.$(date +%Y%m%d).sql'"
```

### Restore

```bash
cp instance/app_state_sqlite.db.bak.20260101 instance/app_state_sqlite.db
```

## Redis Dump

```bash
# Save current RDB
redis-cli -h ${REDIS_HOST:-127.0.0.1} -p ${REDIS_PORT:-6379} BGSAVE

# Copy the dump file
cp /var/lib/redis/dump.rdb /opt/quant-atlas/backups/redis_dump_$(date +%Y%m%d).rdb
```

## File-Based Backups

Backup user-configured files:

```bash
tar czf quant_atlas_config_$(date +%Y%m%d).tar.gz \
  config/users.json \
  config/watchlist.json \
  config/stock_groups.json \
  config/model_registry.json
```

## Restoration Checklist

1. [ ] Stop application services (`flask`, `celery worker`, `celery beat`)
2. [ ] Verify backup file integrity:
   - MySQL: `mysql ... < backup.sql --one-transaction` (dry run)
   - SQLite: `sqlite3 backup.db "PRAGMA integrity_check;"`
3. [ ] Perform restore
4. [ ] Start application services
5. [ ] Run smoke test: `pytest tests/smoke/ -v`
6. [ ] Verify key data counts (users, watchlists, strategies)
7. [ ] Document restoration time and any issues

## Recovery Time Objectives

| Data | RPO | RTO | Method |
|------|-----|-----|--------|
| MySQL | 24h (daily) | 30 min | mysqldump + gzip |
| SQLite | 24h (daily) | 5 min | file copy |
| Redis | Last BGSAVE | 5 min | dump.rdb restore |
| Config files | 24h (daily) | 5 min | tar extract |
