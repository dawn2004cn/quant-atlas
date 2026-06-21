#!/usr/bin/env python
"""Watchlist user isolation migration script

Usage:
    python run_watchlist_user_migration.py --mysql
    python run_watchlist_user_migration.py --sqlite
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
        result = conn.execute(text("SHOW COLUMNS FROM stock_groups LIKE 'user_id'"))
        has_user_id = result.fetchone() is not None

        if not has_user_id:
            print("Migrating stock_groups table...")
            conn.execute(text("ALTER TABLE stock_groups ADD COLUMN user_id INT NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX ix_stock_groups_user_id ON stock_groups(user_id)"))
            conn.execute(text("CREATE UNIQUE INDEX ix_stock_groups_user_id_name ON stock_groups(user_id, name)"))
            print("[OK] stock_groups table migrated")
        else:
            print("stock_groups.user_id column already exists, skip")

        result = conn.execute(text("SHOW COLUMNS FROM stock_group_items LIKE 'user_id'"))
        has_user_id = result.fetchone() is not None

        if not has_user_id:
            print("Migrating stock_group_items table...")
            conn.execute(text("ALTER TABLE stock_group_items ADD COLUMN user_id INT NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX ix_stock_group_items_user_id ON stock_group_items(user_id)"))
            print("[OK] stock_group_items table migrated")
        else:
            print("stock_group_items.user_id column already exists, skip")

        result = conn.execute(text("SHOW COLUMNS FROM watchlist LIKE 'user_id'"))
        has_user_id = result.fetchone() is not None

        if not has_user_id:
            print("Migrating watchlist table...")
            conn.execute(text("ALTER TABLE watchlist ADD COLUMN user_id INT NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX ix_watchlist_user_id ON watchlist(user_id)"))
            print("[OK] watchlist table migrated")
        else:
            print("watchlist.user_id column already exists, skip")

        conn.commit()

    print("\n[SUCCESS] MySQL migration done!")


def migrate_sqlite(db_path: str):
    """Execute SQLite migration"""
    engine = create_engine(f"sqlite:///{db_path}")

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(stock_groups)"))
        columns = {row[1] for row in result.fetchall()}

        if 'user_id' not in columns:
            print("Migrating stock_groups table...")
            conn.execute(text("ALTER TABLE stock_groups ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_stock_groups_user_id ON stock_groups(user_id)"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_stock_groups_user_id_name ON stock_groups(user_id, name)"))
            print("[OK] stock_groups table migrated")
        else:
            print("stock_groups.user_id column already exists, skip")

        result = conn.execute(text("PRAGMA table_info(stock_group_items)"))
        columns = {row[1] for row in result.fetchall()}

        if 'user_id' not in columns:
            print("Migrating stock_group_items table...")
            conn.execute(text("ALTER TABLE stock_group_items ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_stock_group_items_user_id ON stock_group_items(user_id)"))
            print("[OK] stock_group_items table migrated")
        else:
            print("stock_group_items.user_id column already exists, skip")

        result = conn.execute(text("PRAGMA table_info(watchlist)"))
        columns = {row[1] for row in result.fetchall()}

        if 'user_id' not in columns:
            print("Migrating watchlist table...")
            conn.execute(text("ALTER TABLE watchlist ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_watchlist_user_id ON watchlist(user_id)"))
            print("[OK] watchlist table migrated")
        else:
            print("watchlist.user_id column already exists, skip")

        conn.commit()

    print("\n[SUCCESS] SQLite migration done!")


def main():
    parser = argparse.ArgumentParser(description="Watchlist user isolation migration")
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