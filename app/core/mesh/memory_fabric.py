"""Memory Fabric - Associative Vector Store for Cognitive Memory Fabric (Phase 12.1)."""
from __future__ import annotations

import hashlib
import threading
from datetime import datetime, timezone
from typing import Any

from app.core.mesh.perception_layer import text_to_embedding


class MemoryEntry:
    """A memory entry with vector embedding."""

    def __init__(self, entry_id: str, content: str, embedding: list[float], metadata: dict[str, Any] | None = None):
        self.entry_id = entry_id
        self.content = content
        self.embedding = embedding
        self.metadata = metadata or {}
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.access_count = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "access_count": self.access_count,
        }


class MemoryFabric:
    """Associative Vector Store for cross-temporal memory retrieval.

    Stores ArbiterVerdict historical records with vector embeddings for semantic search.
    Enables agents to recall past similar scenarios during current reasoning.
    """

    def __init__(self, dimensions: int = 128):
        self._dimensions = dimensions
        self._entries: dict[str, MemoryEntry] = {}
        self._lock = threading.Lock()
        self._index: list[str] = []

    def index_verdict(self, verdict: dict[str, Any], feedback: str | None = None) -> str:
        """Index an ArbiterVerdict with optional user feedback."""
        content_parts = [
            f"symbol:{verdict.get('symbol', 'unknown')}",
            f"verdict:{verdict.get('meta_verdict', 'neutral')}",
            f"confidence:{verdict.get('meta_confidence', 0):.2f}",
            f"market:{verdict.get('market', 'CN')}",
        ]
        if feedback:
            content_parts.append(f"feedback:{feedback}")
        content = " | ".join(content_parts)

        entry_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        embedding = text_to_embedding(content, dimensions=self._dimensions)

        metadata = {
            "verdict_type": verdict.get("meta_verdict"),
            "symbol": verdict.get("symbol"),
            "market": verdict.get("market"),
            "confidence": verdict.get("meta_confidence"),
            "team_count": verdict.get("team_count"),
        }

        entry = MemoryEntry(entry_id=f"mem-{entry_id}", content=content, embedding=embedding, metadata=metadata)

        with self._lock:
            self._entries[entry.entry_id] = entry
            self._index.append(entry.entry_id)

        return entry.entry_id

    def index_user_feedback(self, user_id: str | int, feedback: dict[str, Any]) -> str:
        """Index a user trading-feedback event for archetype synthesis."""
        content_parts = [
            f"user:{user_id}",
            f"symbols:{','.join(str(item) for item in feedback.get('symbols', []) if item)}",
            f"sectors:{','.join(str(item) for item in feedback.get('sectors', []) if item)}",
            f"factors:{','.join(str(item) for item in feedback.get('factors', []) if item)}",
            f"action:{feedback.get('action', 'view')}",
            f"outcome:{feedback.get('outcome', 'neutral')}",
        ]
        content = " | ".join(content_parts)
        entry_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        embedding = text_to_embedding(content, dimensions=self._dimensions)
        metadata = {
            "user_id": str(user_id),
            "symbols": feedback.get("symbols", []),
            "sectors": feedback.get("sectors", []),
            "factors": feedback.get("factors", []),
            "action": feedback.get("action", "view"),
            "outcome": feedback.get("outcome", "neutral"),
            "feedback_type": "user_knowledge",
        }
        entry = MemoryEntry(entry_id=f"user-{entry_id}", content=content, embedding=embedding, metadata=metadata)
        with self._lock:
            self._entries[entry.entry_id] = entry
            self._index.append(entry.entry_id)
        return entry.entry_id

    def get_feedback_history(self, user_id: str | int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get user feedback memories, optionally filtered by user."""
        with self._lock:
            entries = list(self._entries.values())
            entries = [entry for entry in entries if entry.metadata.get("feedback_type") == "user_knowledge"]
            if user_id is not None:
                entries = [entry for entry in entries if entry.metadata.get("user_id") == str(user_id)]
            return [entry.to_dict() for entry in entries[-limit:]]

    def query_similar(self, query: str, top_k: int = 5, min_similarity: float = 0.6) -> list[dict[str, Any]]:
        """Find similar memories by semantic query."""
        query_emb = text_to_embedding(query, dimensions=self._dimensions)

        results = []
        with self._lock:
            entries = list(self._entries.values())
            for entry in entries:
                sim = _cosine(entry.embedding, query_emb)
                if sim >= min_similarity:
                    entry.access_count += 1
                    results.append({"memory": entry.to_dict(), "similarity": round(sim, 4)})

        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]

    def get_history(self, symbol: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get memory history, optionally filtered by symbol."""
        with self._lock:
            entries = list(self._entries.values())
            if symbol:
                entries = [e for e in entries if e.metadata.get("symbol") == symbol]
            return [e.to_dict() for e in entries[-limit:]]

    def stats(self) -> dict[str, Any]:
        """Get memory fabric statistics."""
        with self._lock:
            return {
                "total_entries": len(self._entries),
                "dimension": self._dimensions,
            }


def _cosine(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity."""
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


_memory_fabric: MemoryFabric | None = None


def get_memory_fabric() -> MemoryFabric:
    global _memory_fabric
    if _memory_fabric is None:
        _memory_fabric = MemoryFabric()
    return _memory_fabric


__all__ = ["MemoryFabric", "MemoryEntry", "get_memory_fabric"]
