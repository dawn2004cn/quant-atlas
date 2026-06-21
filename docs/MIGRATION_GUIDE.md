# Database Migration Guide

> Use Alembic to manage schema changes across environments.

## Quick Reference

```bash
# Create a new migration
alembic revision --autogenerate -m "describe the change"

# Apply all pending migrations
alembic upgrade head

# Roll back one revision
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision>

# Check current revision
alembic current

# Show migration history
alembic history --verbose
```

## Environment Setup

Before running migrations, ensure:

1. `DATABASE_BACKEND=mysql` (or `sqlite` for local dev)
2. `QUANT_DATABASE_URI` or env vars are set:
   - `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
3. Database server is running and accessible

## Migration Files

All migrations live in `alembic/versions/`. Each migration is a Python file with `upgrade()` and `downgrade()` functions.

## Common Tasks

### Adding a new table

```bash
# 1. Add the SQLAlchemy model
# 2. Generate migration
alembic revision --autogenerate -m "add_my_table"
# 3. Review the generated migration for correctness
# 4. Apply
alembic upgrade head
```

### Rolling back data

If you need to undo both schema and data changes:

```bash
# 1. Note the current revision
alembic current

# 2. Downgrade to the target revision
alembic downgrade <target_revision>

# 3. Verify schema is restored
```

> **Warning**: `downgrade` will execute `downgrade()` in the migration file. Ensure it handles data loss correctly.

### Manual SQL for emergency fixes

If Alembic is unavailable, you can run SQL directly:

```bash
mysql -h $MYSQL_HOST -u $MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE -e "SHOW CREATE TABLE your_table;"
```

## CI Migration Check

Add to your CI pipeline:

```yaml
- name: Check migration readiness
  run: |
    alembic upgrade head  # Should succeed without errors
    alembic downgrade base  # Should succeed (reversible)
    alembic upgrade head    # Should be idempotent
```
