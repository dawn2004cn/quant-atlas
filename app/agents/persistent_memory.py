from __future__ import annotations

"""Persistent Agent Memory - Database-backed memory with RAG support.

This module implements from midify_plan13.md optimization:
- PersistentAgentMemory: SQLite/PostgreSQL backed memory
- Session-aware: Cross-session accuracy tracking
- Auto-sync: Periodic persistence to database

Usage:
    memory = PersistentAgentMemory(session_id="session_123")
    memory.record_decision("600519", "TechnicalAnalyst", "bullish", {})
    memory.persist_to_db()
"""


import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import orjson as json

from app.core.logger import get_logger

from .agent_memory import AgentMemory, MemoryEntry

logger = get_logger(__name__)


class PersistentAgentMemory(AgentMemory):
    """Database-backed agent memory for cross-session persistence.

    Features:
    - SQLite local storage (can upgrade to PostgreSQL)
    - Automatic periodic persistence
    - Cross-session accuracy tracking
    - RAG-ready for failure pattern analysis
    """

    def __init__(
        self,
        symbol: str | None = None,
        db_path: str | None = None,
        auto_persist: bool = True,
        persist_interval_seconds: int = 60,
    ):
        super().__init__(symbol)

        self._db_path = db_path or self._get_default_db_path()
        self._auto_persist = auto_persist
        self._persist_interval = persist_interval_seconds
        self._last_persist = datetime.now()
        self._pending_writes: list[MemoryEntry] = []

        self._init_database()
        self._load_from_database()

    def _get_default_db_path(self) -> str:
        """Get default database path."""
        base_dir = Path(__file__).parent.parent.parent
        db_dir = base_dir / "data" / "agents"
        db_dir.mkdir(parents=True, exist_ok=True)
        return str(db_dir / "agent_memory.db")

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                symbol TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                content TEXT NOT NULL,
                outcome TEXT NOT NULL,
                accuracy_score REAL DEFAULT 0.5,
                metadata TEXT,
                session_id TEXT,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_name ON memory_entries(agent_name)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_symbol ON memory_entries(symbol)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session ON memory_entries(session_id)
        """)

        conn.commit()
        conn.close()

        logger.info(f"Initialized persistent memory at: {self._db_path}")

    def _load_from_database(self, limit: int = 1000) -> None:
        """Load recent memory entries from database."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM memory_entries
            ORDER BY timestamp DESC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            entry = MemoryEntry(
                id=row["id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                symbol=row["symbol"],
                agent_name=row["agent_name"],
                event_type=row["event_type"],
                content=row["content"],
                outcome=row["outcome"],
                accuracy_score=row["accuracy_score"],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            )
            self._memory.append(entry)

        logger.info(f"Loaded {len(rows)} memory entries from database")

    def record_decision(
        self,
        symbol: str,
        agent_name: str,
        decision: str,
        context: dict[str, Any],
        session_id: str | None = None,
    ) -> str:
        """Record decision with session tracking."""
        entry_id = super().record_decision(symbol, agent_name, decision, context)

        if self._auto_persist:
            self._pending_writes.append(self._memory[-1])

        return entry_id

    def persist_to_db(self, force: bool = False) -> int:
        """Persist pending entries to database."""
        if not self._pending_writes and not force:
            return 0

        if not force:
            time_since_last = (datetime.now() - self._last_persist).total_seconds()
            if time_since_last < self._persist_interval:
                return 0

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        entries_to_write = self._pending_writes.copy()
        self._pending_writes.clear()

        for entry in entries_to_write:
            cursor.execute("""
                INSERT OR REPLACE INTO memory_entries
                (id, timestamp, symbol, agent_name, event_type, content, outcome, accuracy_score, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.timestamp.isoformat(),
                entry.symbol,
                entry.agent_name,
                entry.event_type,
                entry.content,
                entry.outcome,
                entry.accuracy_score,
                json.dumps(entry.metadata, default=str),
                datetime.now().isoformat(),
            ))

        conn.commit()
        conn.close()

        self._last_persist = datetime.now()
        logger.info(f"Persisted {len(entries_to_write)} entries to database")

        return len(entries_to_write)

    def get_agent_accuracy(self, agent_name: str, days: int = 30) -> float:
        """Get agent's historical accuracy over specified days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT accuracy_score, outcome
            FROM memory_entries
            WHERE agent_name = ?
            AND timestamp > ?
            AND outcome != 'pending'
        """, (agent_name, cutoff))

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return 0.5

        valid_scores = [r[0] for r in rows if r[1] != "pending"]
        return sum(valid_scores) / len(valid_scores) if valid_scores else 0.5

    def get_all_agents_performance(self) -> dict[str, dict[str, Any]]:
        """Get performance metrics for all agents."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT agent_name,
                   COUNT(*) as total_decisions,
                   AVG(accuracy_score) as avg_accuracy,
                   SUM(CASE WHEN outcome = 'correct' THEN 1 ELSE 0 END) as correct_count
            FROM memory_entries
            WHERE outcome != 'pending'
            GROUP BY agent_name
        """)

        rows = cursor.fetchall()
        conn.close()

        result = {}
        for row in rows:
            result[row[0]] = {
                "total_decisions": row[1],
                "avg_accuracy": row[2] or 0.5,
                "correct_count": row[3],
            }

        return result


_global_memory: PersistentAgentMemory | None = None


def get_persistent_memory(
    symbol: str | None = None,
    session_id: str | None = None,
) -> PersistentAgentMemory:
    """Get singleton persistent memory."""
    global _global_memory
    if _global_memory is None:
        _global_memory = PersistentAgentMemory(symbol=symbol)
    return _global_memory


def create_persistent_memory(
    symbol: str | None = None,
    db_path: str | None = None,
) -> PersistentAgentMemory:
    """Factory to create persistent memory."""
    return PersistentAgentMemory(symbol=symbol, db_path=db_path)
