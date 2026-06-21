"""SQLite-backed order state persistence."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_CREATE_ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    order_id TEXT PRIMARY KEY,
    state TEXT,
    data TEXT,
    updated_at REAL
)
"""


class SqliteOrderPersistenceBackend:
    """Persist order state in a local SQLite database."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: dict[str, Any]) -> bool:
        conn = sqlite3.connect(str(self._db_path))
        try:
            conn.execute(_CREATE_ORDERS_TABLE)
            for order_id, data in state.items():
                conn.execute(
                    "INSERT OR REPLACE INTO orders (order_id, state, data, updated_at) VALUES (?, ?, ?, ?)",
                    (order_id, data.get("state", ""), json.dumps(data), time.time()),
                )
            conn.commit()
            return True
        except Exception as exc:
            logger.error("SQLite save failed: %s", exc)
            return False
        finally:
            conn.close()

    def load_state(self) -> dict[str, Any]:
        if not self._db_path.exists():
            return {}
        conn = sqlite3.connect(str(self._db_path))
        try:
            cursor = conn.execute("SELECT order_id, data FROM orders")
            return {order_id: json.loads(data) for order_id, data in cursor}
        except Exception as exc:
            logger.error("SQLite load failed: %s", exc)
            return {}
        finally:
            conn.close()
