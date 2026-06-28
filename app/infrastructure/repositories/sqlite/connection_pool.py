from __future__ import annotations

"""Shared SQLite connection pool for all SQLite repositories.

Replaces per-repository independent sqlite3.connect() calls with a
shared pool, preventing write-deadlocks under concurrent access.
"""

import sqlite3
import threading
from collections import OrderedDict


class SQLiteConnectionPool:
    """Thread-safe LRU connection pool for SQLite."""

    def __init__(self, max_connections_per_path: int = 4, max_paths: int = 16):
        self._max_per_path = max_connections_per_path
        self._max_paths = max_paths
        self._pools: dict[str, OrderedDict[int, sqlite3.Connection]] = {}
        self._in_use: dict[str, set[int]] = {}
        self._counter: dict[str, int] = {}
        self._lock = threading.Lock()

    def get_connection(self, db_path: str) -> sqlite3.Connection:
        with self._lock:
            if db_path not in self._pools:
                if len(self._pools) >= self._max_paths:
                    self._evict_one()
                self._pools[db_path] = OrderedDict()
                self._in_use[db_path] = set()
            pool = self._pools[db_path]
            if pool:
                cid, conn = pool.popitem(last=False)
                self._in_use[db_path].add(cid)
                return conn
            cid = self._counter.get(db_path, 0) + 1
            self._counter[db_path] = cid
            conn = self._create_connection(db_path)
            self._in_use[db_path].add(cid)
            return conn

    def put_connection(self, db_path: str, conn: sqlite3.Connection) -> None:
        with self._lock:
            cid = id(conn)
            self._in_use.get(db_path, set()).discard(cid)
            pool = self._pools.get(db_path, {})
            if len(pool) < self._max_per_path:
                pool[cid] = conn
            else:
                conn.close()

    def close_all(self) -> None:
        with self._lock:
            for db_path, pool in self._pools.items():
                for cid, conn in pool.items():
                    try:
                        conn.close()
                    except Exception:
                        pass
            self._pools.clear()
            self._in_use.clear()
            self._counter.clear()

    def _evict_one(self) -> None:
        for db_path in list(self._pools.keys()):
            if not self._in_use.get(db_path, set()):
                pool = self._pools.pop(db_path, {})
                for cid, conn in pool.items():
                    try:
                        conn.close()
                    except Exception:
                        pass
                return

    @staticmethod
    def _create_connection(db_path: str) -> sqlite3.Connection:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn


sqlite_pool = SQLiteConnectionPool()
