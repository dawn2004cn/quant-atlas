"""SQLite implementation of OpenBBRepository."""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from app.domain.market_entities import ProviderConfig
from app.domain.ports import OpenBBRepository


class SQLiteOpenBBRepository(OpenBBRepository):
    """SQLite implementation of OpenBBRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS openbb_provider_configs (
                    provider_name TEXT PRIMARY KEY,
                    is_enabled INTEGER DEFAULT 1,
                    settings_json TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS openbb_data_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    timeframe TEXT,
                    payload_json TEXT,
                    expires_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS openbb_kv_store (
                    key TEXT PRIMARY KEY,
                    payload_json TEXT,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def save_data(self, key: str, data: Any) -> bool:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO openbb_kv_store (key, payload_json, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    payload_json=excluded.payload_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (key, json.dumps(data) if data is not None else "null"),
            )
            conn.commit()
        return True

    def get_data(self, key: str) -> Any | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT payload_json FROM openbb_kv_store WHERE key=?",
                (key,),
            )
            row = cur.fetchone()
        return json.loads(row["payload_json"]) if row else None

    def get_provider_config(self, provider_name: str) -> ProviderConfig | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM openbb_provider_configs WHERE provider_name = ?",
                (provider_name,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return ProviderConfig(
                provider_name=row["provider_name"],
                is_enabled=bool(row["is_enabled"]),
                settings=json.loads(row["settings_json"]) if row["settings_json"] else {},
                updated_at=row["updated_at"]
            )

    def save_provider_config(self, config: ProviderConfig) -> None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM openbb_provider_configs WHERE provider_name = ?",
                (config.provider_name,)
            )
            existing = cur.fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO openbb_provider_configs (provider_name, is_enabled, settings_json)
                    VALUES (?, ?, ?)
                    """,
                    (
                        config.provider_name,
                        1 if config.is_enabled else 0,
                        json.dumps(config.settings) if config.settings else "{}"
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE openbb_provider_configs SET
                        is_enabled = ?,
                        settings_json = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE provider_name = ?
                    """,
                    (
                        1 if config.is_enabled else 0,
                        json.dumps(config.settings) if config.settings else "{}",
                        config.provider_name
                    )
                )
            conn.commit()

    def get_cached_data(self, provider: str, symbol: str, data_type: str, timeframe: str | None = None) -> Any:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT * FROM openbb_data_cache
                WHERE provider = ? AND symbol = ? AND data_type = ? AND timeframe = ? AND expires_at > ?
                """,
                (provider, symbol, data_type, timeframe, now)
            )
            row = cur.fetchone()
            if row:
                return json.loads(row["payload_json"])
            return None

    def cache_data(self, provider: str, symbol: str, data_type: str, payload: Any, timeframe: str | None = None, ttl_hours: int = 24) -> None:
        expires_at = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO openbb_data_cache (provider, symbol, data_type, timeframe, payload_json, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    symbol,
                    data_type,
                    timeframe,
                    json.dumps(payload) if payload else "{}",
                    expires_at
                )
            )
            conn.commit()
