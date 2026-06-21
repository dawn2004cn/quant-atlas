#!/usr/bin/env python
"""Signal observations table migration script

Usage:
    python run_signal_observations_migration.py --mysql
    python run_signal_observations_migration.py --sqlite
"""

import argparse
import sys
import os
from pathlib import Path

os.environ['PYTHONIOENCODING'] = 'utf-8'

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text


def migrate_mysql(mysql_url: str):
    """Execute MySQL migration"""
    engine = create_engine(mysql_url)

    with engine.connect() as conn:
        # Create signal_observations table
        result = conn.execute(text("SHOW TABLES LIKE 'signal_observations'"))
        if result.fetchone() is None:
            print("Creating signal_observations table...")
            conn.execute(text("""
                CREATE TABLE signal_observations (
                    id VARCHAR(12) PRIMARY KEY,
                    user_id INT NOT NULL DEFAULT 1,
                    symbol VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'CN',
                    name VARCHAR(100),
                    entry_price DECIMAL(10,4),
                    current_price DECIMAL(10,4),
                    stop_loss DECIMAL(10,4),
                    target_price DECIMAL(10,4),
                    source VARCHAR(50) DEFAULT 'manual',
                    reason VARCHAR(500),
                    ai_summary TEXT,
                    status VARCHAR(20) DEFAULT 'open',
                    trigger_status VARCHAR(20) DEFAULT 'watching',
                    created_at DATETIME,
                    updated_at DATETIME,
                    closed_at DATETIME,
                    close_reason VARCHAR(200),
                    peak_price DECIMAL(10,4),
                    trough_price DECIMAL(10,4),
                    max_gain_pct DECIMAL(10,4) DEFAULT 0,
                    max_drawdown_pct DECIMAL(10,4) DEFAULT 0,
                    notes TEXT,
                    INDEX idx_signal_obs_user (user_id),
                    INDEX idx_signal_obs_status (status),
                    INDEX idx_signal_obs_symbol (symbol),
                    INDEX idx_signal_obs_created (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            print("[OK] signal_observations table created")
        else:
            print("signal_observations table already exists, skip")

        # Add missing columns if they don't exist
        for col in ["return_pct", "change_pct"]:
            try:
                conn.execute(text(f"ALTER TABLE signal_observations ADD COLUMN {col} DECIMAL(10,4) DEFAULT 0"))
                conn.commit()
                print(f"[OK] Added {col} column")
            except:
                pass

        # Create signal_observation_positions table
        result = conn.execute(text("SHOW TABLES LIKE 'signal_observation_positions'"))
        if result.fetchone() is None:
            print("Creating signal_observation_positions table...")
            conn.execute(text("""
                CREATE TABLE signal_observation_positions (
                    id VARCHAR(12) PRIMARY KEY,
                    user_id INT NOT NULL DEFAULT 1,
                    observation_id VARCHAR(12),
                    symbol VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'CN',
                    name VARCHAR(100),
                    shares INT DEFAULT 100,
                    cost_basis DECIMAL(10,4),
                    current_price DECIMAL(10,4),
                    total_cost DECIMAL(12,4),
                    total_value DECIMAL(12,4),
                    pnl DECIMAL(12,4),
                    return_pct DECIMAL(10,4),
                    max_gain_pct DECIMAL(10,4) DEFAULT 0,
                    max_drawdown_pct DECIMAL(10,4) DEFAULT 0,
                    source VARCHAR(50),
                    converted_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME,
                    INDEX idx_pos_user (user_id),
                    INDEX idx_pos_symbol (symbol),
                    INDEX idx_pos_converted (converted_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            print("[OK] signal_observation_positions table created")
        else:
            print("signal_observation_positions table already exists, skip")

        conn.commit()

    print("\n[SUCCESS] MySQL migration done!")


def migrate_sqlite(db_path: str):
    """Execute SQLite migration"""
    engine = create_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        # Create signal_observations table
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_observations'"))
        if result.fetchone() is None:
            print("Creating signal_observations table...")
            conn.execute(text("""
                CREATE TABLE signal_observations (
                    id VARCHAR(12) PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    symbol VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'CN',
                    name VARCHAR(100),
                    entry_price REAL,
                    current_price REAL,
                    stop_loss REAL,
                    target_price REAL,
                    source VARCHAR(50) DEFAULT 'manual',
                    reason VARCHAR(500),
                    ai_summary TEXT,
                    status VARCHAR(20) DEFAULT 'open',
                    trigger_status VARCHAR(20) DEFAULT 'watching',
                    created_at TEXT,
                    updated_at TEXT,
                    closed_at TEXT,
                    close_reason VARCHAR(200),
                    peak_price REAL,
                    trough_price REAL,
                    max_gain_pct REAL DEFAULT 0,
                    max_drawdown_pct REAL DEFAULT 0,
                    notes TEXT
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_signal_obs_user ON signal_observations(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_signal_obs_status ON signal_observations(status)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_signal_obs_symbol ON signal_observations(symbol)"))
            print("[OK] signal_observations table created")
        else:
            print("signal_observations table already exists, skip")

        # Create signal_observation_positions table
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_observation_positions'"))
        if result.fetchone() is None:
            print("Creating signal_observation_positions table...")
            conn.execute(text("""
                CREATE TABLE signal_observation_positions (
                    id VARCHAR(12) PRIMARY KEY,
                    user_id INTEGER NOT NULL DEFAULT 1,
                    observation_id VARCHAR(12),
                    symbol VARCHAR(20) NOT NULL,
                    market VARCHAR(10) NOT NULL DEFAULT 'CN',
                    name VARCHAR(100),
                    shares INTEGER DEFAULT 100,
                    cost_basis REAL,
                    current_price REAL,
                    total_cost REAL,
                    total_value REAL,
                    pnl REAL,
                    return_pct REAL,
                    max_gain_pct REAL DEFAULT 0,
                    max_drawdown_pct REAL DEFAULT 0,
                    source VARCHAR(50),
                    converted_at TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pos_user ON signal_observation_positions(user_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_pos_symbol ON signal_observation_positions(symbol)"))
            print("[OK] signal_observation_positions table created")
        else:
            print("signal_observation_positions table already exists, skip")

        conn.commit()

    print("\n[SUCCESS] SQLite migration done!")


def main():
    parser = argparse.ArgumentParser(description="Signal observations table migration")
    parser.add_argument("--mysql", action="store_true", help="Run MySQL migration")
    parser.add_argument("--sqlite", action="store_true", help="Run SQLite migration")
    parser.add_argument("--url", type=str, help="MySQL connection URL")
    parser.add_argument("--db-path", type=str, help="SQLite database file path")

    args = parser.parse_args()

    if args.mysql:
        if not args.url:
            print("Error: Please specify MySQL connection URL via --url")
            print("Example: mysql+pymysql://user:password@localhost:3306/quant_atlas")
            sys.exit(1)
        migrate_mysql(args.url)

    elif args.sqlite:
        if not args.db_path:
            print("Error: Please specify SQLite database file path via --db-path")
            sys.exit(1)
        migrate_sqlite(args.db_path)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()