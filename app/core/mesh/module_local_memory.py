from __future__ import annotations
"""Module-local memory — namespace-isolated lesson store per context module.

Each ``ContextModule`` gets a ``ModuleLocalMemory`` that persists rebalancing
lessons, failure patterns, and successful strategies as compact JSONL records.
"""


import json
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModuleMemoryEntry:
    memory_id: str
    module_name: str
    memory_type: str  # "lesson" | "pattern" | "constraint" | "success" | "failure"
    description: str
    symbol: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    access_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModuleLocalMemory:
    """JSONL-backed local memory for a single context module.

    Thread-safe, append-only, with in-memory LRU cache for hot reads.
    """

    def __init__(self, module_name: str, store_path: Path | str | None = None) -> None:
        self._module_name = module_name
        if store_path is None:
            root = Path(__file__).resolve().parents[4]
            store_path = root / "instance" / f"module_memory_{module_name}.jsonl"
        self._store_path = Path(store_path)
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._cache: list[ModuleMemoryEntry] | None = None

    def remember(
        self,
        memory_type: str,
        description: str,
        *,
        symbol: str = "",
        context: dict[str, Any] | None = None,
        score: float = 0.0,
    ) -> ModuleMemoryEntry:
        import uuid

        entry = ModuleMemoryEntry(
            memory_id=f"{self._module_name}_{uuid.uuid4().hex[:12]}",
            module_name=self._module_name,
            memory_type=memory_type,
            description=description,
            symbol=symbol,
            context=context or {},
            score=score,
        )
        with self._lock:
            with open(self._store_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
            if self._cache is not None:
                self._cache.append(entry)
        return entry

    def remember_lesson(
        self,
        *,
        symbol: str = "",
        context: dict[str, Any] | None = None,
        score: float = 0.0,
        description: str = "portfolio lesson",
    ) -> ModuleMemoryEntry:
        return self.remember("lesson", description, symbol=symbol, context=context, score=score)

    def recall_lessons(self, symbol: str | None = None, top_k: int = 5) -> list[ModuleMemoryEntry]:
        return self.recall(memory_type="lesson", symbol=symbol, top_k=top_k)

    def load_all(self) -> list[ModuleMemoryEntry]:
        return self._load_all()

    def get_memory_stats(self) -> dict[str, Any]:
        return self.stats()

    def recall(
        self,
        *,
        memory_type: str | None = None,
        symbol: str | None = None,
        top_k: int = 10,
        min_score: float = 0.0,
    ) -> list[ModuleMemoryEntry]:
        all_entries = self._load_all()
        filtered = [
            e for e in all_entries
            if (memory_type is None or e.memory_type == memory_type)
            and (symbol is None or e.symbol == symbol)
            and e.score >= min_score
        ]
        filtered.sort(key=lambda e: e.score, reverse=True)
        return filtered[:top_k]

    def stats(self) -> dict[str, Any]:
        entries = self._load_all()
        type_counts: dict[str, int] = {}
        for e in entries:
            type_counts[e.memory_type] = type_counts.get(e.memory_type, 0) + 1
        return {
            "module": self._module_name,
            "total_entries": len(entries),
            "by_type": type_counts,
            "store_path": str(self._store_path),
        }

    def _load_all(self) -> list[ModuleMemoryEntry]:
        if self._cache is not None:
            return self._cache
        entries: list[ModuleMemoryEntry] = []
        if self._store_path.exists():
            with self._lock:
                with open(self._store_path, encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                entries.append(ModuleMemoryEntry(**data))
                            except Exception:
                                continue
                self._cache = entries
        return entries

    def clear_cache(self) -> None:
        with self._lock:
            self._cache = None
