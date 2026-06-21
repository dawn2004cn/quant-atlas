"""Final P0 migration: fix TEXT DEFAULT issue, stamp alembic_version."""
import os
os.environ.setdefault('STRICT_BOOTSTRAP', '0')

from app.config import AppSettings
from app.infrastructure.database.orm import create_db_engine
from sqlalchemy import text

s = AppSettings.from_env()
engine = create_db_engine(s.database_uri)

with engine.connect() as conn:
    # 1. Stamp alembic_version
    try:
        result = conn.execute(text("SELECT VERSION_NUM FROM alembic_version LIMIT 1"))
        row = result.fetchone()
        if row is None:
            conn.execute(text("INSERT INTO alembic_version VALUES ('add_user_id_stock_groups')"))
            print("Stamped alembic_version.")
        else:
            print(f"alembic_version already stamped: {row[0]}")
    except Exception as e:
        print(f"alembic_version: {e}")

    # 2. roles.permissions_json
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='roles' AND COLUMN_NAME='permissions_json'
        """))
        has = result.fetchone()[0] > 0
        if not has:
            conn.execute(text("ALTER TABLE roles ADD COLUMN permissions_json TEXT"))
            print("Added roles.permissions_json")
        else:
            print("roles.permissions_json exists")
    except Exception as e:
        print(f"roles.permissions_json: {e}")

    # 3. audit_events — may already exist
    try:
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.TABLES
            WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='audit_events'
        """))
        exists = result.fetchone()[0] > 0
        if not exists:
            conn.execute(text("""
                CREATE TABLE audit_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    snapshot_id VARCHAR(64) NOT NULL UNIQUE,
                    order_id VARCHAR(64) NOT NULL,
                    user_id INT NOT NULL,
                    symbol VARCHAR(32) NOT NULL,
                    action VARCHAR(16) NOT NULL,
                    quantity INT NOT NULL,
                    price DOUBLE NOT NULL,
                    ai_evidence_json TEXT,
                    factor_values_json TEXT,
                    risk_assessment_json TEXT,
                    compliance_result_json TEXT,
                    timestamp VARCHAR(64) NOT NULL DEFAULT '',
                    previous_hash VARCHAR(64) NOT NULL DEFAULT 'genesis',
                    content_hash VARCHAR(64) NOT NULL,
                    chain_hash VARCHAR(64) NOT NULL,
                    INDEX idx_snapshot(snapshot_id),
                    INDEX idx_order(order_id),
                    INDEX idx_user(user_id),
                    INDEX idx_symbol(symbol),
                    INDEX idx_timestamp(timestamp)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            print("Created audit_events")
        else:
            print("audit_events exists")
    except Exception as e:
        print(f"audit_events: {e}")

    conn.commit()

print("\nDone.")
