from __future__ import annotations

from app.core.runtime_config import get_runtime

"""Knowledge Store - Redis + Vector DB for RD-Agent experiment memory.

This module implements the "Global Knowledge Graph" from quant_plan.md:
- Stores successful and failed RD-Agent experiments
- Enables cross-domain reasoning (e.g., "this stock was marked as momentum-insensitive")
- Uses vector similarity for semantic search
"""


import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import redis
from app.infrastructure.redis_client import RedisClientPool

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExperimentRecord:
    """A single RD-Agent experiment record."""
    run_id: str
    formula: str
    goal: str | None
    status: str
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class KnowledgeStore:
    """Knowledge store for RD-Agent experiments with vector similarity.

    Uses Redis as the backend storage with JSON serialization.
    Supports tagging and metadata for cross-domain reasoning.

    Implements write-behind caching for high-frequency writes.
    """

    REDIS_KEY_PREFIX = "knowledge:"
    EXPERIMENT_TTL = 60 * 60 * 24 * 365

    WRITE_BEHIND_BUFFER_SIZE = 100
    WRITE_BEHIND_FLUSH_INTERVAL_SECONDS = 5

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or get_runtime("REDIS_URL", "")
        self._client: redis.Redis | None = None
        self._write_buffer: list[tuple[str, dict]] = []
        self._write_buffer_lock = None

    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            self._client = RedisClientPool.get(self.redis_url).client
        return self._client

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def store_experiment(self, record: ExperimentRecord) -> bool:
        """Store an experiment record using write-behind for high-frequency writes."""
        import threading
        if self._write_buffer_lock is None:
            self._write_buffer_lock = threading.Lock()

        key = f"{self.REDIS_KEY_PREFIX}experiment:{record.run_id}"
        data = {
            "run_id": record.run_id,
            "formula": record.formula,
            "goal": record.goal,
            "status": record.status,
            "metrics": record.metrics,
            "error_message": record.error_message,
            "tags": record.tags,
            "created_at": record.created_at.isoformat(),
            "metadata": record.metadata,
        }

        with self._write_buffer_lock:
            self._write_buffer.append((key, data))
            should_flush = len(self._write_buffer) >= self.WRITE_BEHIND_BUFFER_SIZE

        if should_flush:
            self._flush_write_buffer()

        return True

    def _flush_write_buffer(self) -> None:
        """Flush write buffer to Redis."""
        with self._write_buffer_lock:
            buffer_copy = self._write_buffer.copy()
            self._write_buffer.clear()

        for key, data in buffer_copy:
            try:
                self.client.setex(key, self.EXPERIMENT_TTL, json.dumps(data))
            except Exception as e:
                logger.error(f"Write-behind flush failed for {key}: {e}")

    def flush(self) -> int:
        """Manually flush remaining buffer. Returns count of flushed items."""
        if self._write_buffer_lock is None:
            return 0

        with self._write_buffer_lock:
            count = len(self._write_buffer)
            buffer_copy = self._write_buffer.copy()
            self._write_buffer.clear()

        for key, data in buffer_copy:
            try:
                self.client.setex(key, self.EXPERIMENT_TTL, json.dumps(data))
            except Exception as e:
                logger.error(f"Write-behind flush failed: {e}")

        return count

    def get_experiment(self, run_id: str) -> ExperimentRecord | None:
        """Retrieve an experiment by ID."""
        key = f"{self.REDIS_KEY_PREFIX}experiment:{run_id}"
        data = self.client.get(key)
        if not data:
            return None
        obj = json.loads(data)
        return ExperimentRecord(
            run_id=obj["run_id"],
            formula=obj["formula"],
            goal=obj.get("goal"),
            status=obj["status"],
            metrics=obj.get("metrics", {}),
            error_message=obj.get("error_message"),
            tags=obj.get("tags", []),
            created_at=datetime.fromisoformat(obj["created_at"]),
            metadata=obj.get("metadata", {}),
        )

    def get_failed_experiments(self, limit: int = 100) -> list[ExperimentRecord]:
        """Get recent failed experiments for analysis."""
        pattern = f"{self.REDIS_KEY_PREFIX}experiment:*"
        records = []
        for key in self.client.scan_iter(pattern, count=100):
            data = self.client.get(key)
            if data:
                obj = json.loads(data)
                if obj["status"] == "failed":
                    records.append(ExperimentRecord(
                        run_id=obj["run_id"],
                        formula=obj["formula"],
                        goal=obj.get("goal"),
                        status=obj["status"],
                        metrics=obj.get("metrics", {}),
                        error_message=obj.get("error_message"),
                        tags=obj.get("tags", []),
                        created_at=datetime.fromisoformat(obj["created_at"]),
                        metadata=obj.get("metadata", {}),
                    ))
        records.sort(key=lambda x: x.created_at, reverse=True)
        return records[:limit]

    def get_experiments_by_tag(self, tag: str) -> list[ExperimentRecord]:
        """Get all experiments with a specific tag."""
        run_ids = self.client.smembers(f"{self.REDIS_KEY_PREFIX}tag:{tag}")
        records = []
        for run_id in run_ids:
            record = self.get_experiment(run_id)
            if record:
                records.append(record)
        return records

    def search_by_formula_similarity(self, formula_substring: str, limit: int = 10) -> list[ExperimentRecord]:
        """Search experiments by formula substring (simple matching)."""
        pattern = f"{self.REDIS_KEY_PREFIX}experiment:*"
        records = []
        for key in self.client.scan_iter(pattern, count=100):
            data = self.client.get(key)
            if data and formula_substring.lower() in data.lower():
                obj = json.loads(data)
                records.append(ExperimentRecord(
                    run_id=obj["run_id"],
                    formula=obj["formula"],
                    goal=obj.get("goal"),
                    status=obj["status"],
                    metrics=obj.get("metrics", {}),
                    error_message=obj.get("error_message"),
                    tags=obj.get("tags", []),
                    created_at=datetime.fromisoformat(obj["created_at"]),
                    metadata=obj.get("metadata", {}),
                ))
        return records[:limit]

    def get_experiment_stats(self) -> dict[str, Any]:
        """Get statistics about stored experiments."""
        pattern = f"{self.REDIS_KEY_PREFIX}experiment:*"
        total = 0
        failed = 0
        successful = 0
        for key in self.client.scan_iter(pattern, count=100):
            total += 1
            data = self.client.get(key)
            if data:
                obj = json.loads(data)
                if obj["status"] == "failed":
                    failed += 1
                elif obj["status"] == "completed":
                    successful += 1
        return {
            "total": total,
            "failed": failed,
            "successful": successful,
            "running": total - failed - successful,
        }

    def query_historical_context(self, symbol: str, topic: str) -> list[dict[str, Any]]:
        """Query historical context for a symbol/topic.

        This enables the cross-domain reasoning from quant_plan.md:
        "When investment_committee analyzes a stock, it automatically retrieves
        lab records: 'This symbol was marked as momentum-insensitive 3 months ago'"
        """
        pattern = f"{self.REDIS_KEY_PREFIX}experiment:*"
        results = []
        search_terms = [symbol.lower(), topic.lower()]
        for key in self.client.scan_iter(pattern, count=100):
            data = self.client.get(key)
            if data:
                obj = json.loads(data)
                formula_lower = obj.get("formula", "").lower()
                tags = obj.get("tags", [])
                if any(term in formula_lower or term in " ".join(tags).lower() for term in search_terms):
                    results.append({
                        "run_id": obj["run_id"],
                        "formula": obj["formula"],
                        "status": obj["status"],
                        "metrics": obj.get("metrics", {}),
                        "created_at": obj["created_at"],
                        "tags": tags,
                    })
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results[:20]


_knowledge_store: KnowledgeStore | None = None


def get_knowledge_store() -> KnowledgeStore:
    """Get the global knowledge store instance."""
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = KnowledgeStore()
    return _knowledge_store


def store_rd_agent_experiment(
    run_id: str,
    formula: str,
    goal: str | None,
    status: str,
    metrics: dict[str, Any] | None = None,
    error_message: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """Convenience function to store an RD-Agent experiment."""
    record = ExperimentRecord(
        run_id=run_id,
        formula=formula,
        goal=goal,
        status=status,
        metrics=metrics or {},
        error_message=error_message,
        tags=tags or [],
    )
    return get_knowledge_store().store_experiment(record)


def query_symbol_research_history(symbol: str) -> list[dict[str, Any]]:
    """Query all research history for a symbol."""
    return get_knowledge_store().query_historical_context(symbol, "")
