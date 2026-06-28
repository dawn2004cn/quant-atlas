"""LocalMemory injection into PortfolioModule.
Phase 11: gives each portfolio instance its own persistent memory of past lessons."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LocalMemoryEntry:
    """Single learning memory for a portfolio."""
    memory_id: str
    portfolio_id: str
    memory_type: str  # "lesson", "pattern", "constraint", "success"
    description: str
    symbol: str = ""
    weights_before: dict[str, float] = field(default_factory=dict)
    weights_after: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PortfolioLocalMemory:
    """Injects persistent lesson memory into a PortfolioModule instance."""

    def __init__(self, portfolio_id: str | None = None, store_path: Path | str | None = None):
        root = Path(__file__).resolve().parents[4]
        self._store_path = Path(store_path) if store_path else root / "instance" / "portfolio_memory.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, LocalMemoryEntry] = {}
        self.portfolio_id = portfolio_id or f"pf.{uuid.uuid4().hex[:8]}"

    def remember_lesson(self, symbol: str, weights_before: dict, weights_after: dict,
                        description: str, score: float):
        entry = LocalMemoryEntry(
            memory_id=uuid.uuid4().hex[:12],
            portfolio_id=self.portfolio_id,
            memory_type="lesson",
            description=description[:500],
            symbol=symbol,
            weights_before=weights_before,
            weights_after=weights_after,
            score=score,
        )
        self._cache[entry.memory_id] = entry
        self._persist(entry)
        return entry

    def recall_lessons(self, symbol: str | None = None, top_k: int = 5) -> list[LocalMemoryEntry]:
        lessons = [e for e in self._cache.values() if e.memory_type in ("lesson", "pattern")]
        if symbol:
            lessons = [l for l in lessons if l.symbol == symbol]
        lessons.sort(key=lambda l: l.score, reverse=True)
        return lessons[:top_k]

    def recall_signals(self, context: dict) -> list[dict]:
        signals = []
        for lesson in self.recall_lessons():
            signal = {
                "symbol": lesson.symbol,
                "description": lesson.description,
                "score": lesson.score,
                "weight_shift": self._compute_weight_shift(lesson),
            }
            signals.append(signal)
        return signals

    def _compute_weight_shift(self, lesson: LocalMemoryEntry) -> dict:
        shift = {}
        for k in set(list(lesson.weights_before.keys()) + list(lesson.weights_after.keys())):
            before = lesson.weights_before.get(k, 0)
            after = lesson.weights_after.get(k, 0)
            shift[k] = round(after - before, 4)
        return shift

    def _persist(self, entry: LocalMemoryEntry):
        with self._store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.__dict__) + "\n")

    def load_all(self):
        if not self._store_path.exists():
            return []
        entries = []
        with self._store_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    entry = LocalMemoryEntry(**data)
                    self._cache[entry.memory_id] = entry
                    entries.append(entry)
        return entries

    def get_memory_stats(self) -> dict:
        return {
            "portfolio_id": self.portfolio_id,
            "total_entries": len(self._cache),
            "lesson_count": sum(1 for e in self._cache.values() if e.memory_type == "lesson"),
            "pattern_count": sum(1 for e in self._cache.values() if e.memory_type == "pattern"),
        }

    def inject_into_portfolio(self, portfolio_service):
        if hasattr(portfolio_service, "_local_memory"):
            logger.warning("Portfolio already has local memory, overwriting")
        portfolio_service._local_memory = self
        logger.info("LocalMemory injected into portfolio %s", self.portfolio_id)
