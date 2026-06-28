"""Regression tests for ModuleLocalMemory (Phase 11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.mesh.module_local_memory import ModuleLocalMemory


class TestModuleLocalMemory:
    """JSONL-backed per-module lesson store."""

    @pytest.fixture
    def tmp_store(self, tmp_path: Path) -> Path:
        return tmp_path / "test_memory.jsonl"

    def test_remember_persists_entry(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        entry = mem.remember("lesson", "Always check volume before entry", symbol="600519", score=0.9)
        assert entry.memory_type == "lesson"
        assert entry.symbol == "600519"
        assert entry.score == 0.9
        assert entry.module_name == "test_module"
        assert tmp_store.exists()

    def test_recall_returns_sorted_results(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        mem.remember("lesson", "Lesson 1", score=0.5)
        mem.remember("lesson", "Lesson 2", score=0.9)
        mem.remember("lesson", "Lesson 3", score=0.7)

        results = mem.recall(memory_type="lesson", top_k=3)
        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score

    def test_recall_filters_by_symbol(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        mem.remember("pattern", "AAPL pattern", symbol="AAPL", score=0.8)
        mem.remember("pattern", "TSLA pattern", symbol="TSLA", score=0.9)

        results = mem.recall(memory_type="pattern", symbol="AAPL")
        assert len(results) == 1
        assert results[0].symbol == "AAPL"

    def test_recall_filters_by_min_score(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        mem.remember("lesson", "Low score", score=0.3)
        mem.remember("lesson", "High score", score=0.9)

        results = mem.recall(memory_type="lesson", min_score=0.5)
        assert len(results) == 1
        assert results[0].score >= 0.5

    def test_recall_top_k(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        for i in range(10):
            mem.remember("lesson", f"Lesson {i}", score=i / 10)

        results = mem.recall(memory_type="lesson", top_k=3)
        assert len(results) == 3

    def test_recall_nonexistent_type(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        results = mem.recall(memory_type="nonexistent")
        assert results == []

    def test_stats_counts(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        mem.remember("lesson", "L1")
        mem.remember("lesson", "L2")
        mem.remember("pattern", "P1")

        stats = mem.stats()
        assert stats["total_entries"] == 3
        assert stats["by_type"]["lesson"] == 2
        assert stats["by_type"]["pattern"] == 1

    def test_remember_lesson_convenience(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        entry = mem.remember_lesson(description="Always check volume", symbol="600519", score=0.9)
        assert entry.memory_type == "lesson"

    def test_remember_pattern_convenience(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        entry = mem.remember("pattern", "Morning gap up followed by reversal", symbol="000001", score=0.7)
        assert entry.memory_type == "pattern"

    def test_persistence_across_instances(self, tmp_store: Path):
        mem1 = ModuleLocalMemory("test_module", store_path=tmp_store)
        mem1.remember("lesson", "Persistent lesson", score=1.0)

        mem2 = ModuleLocalMemory("test_module", store_path=tmp_store)
        results = mem2.recall(memory_type="lesson")
        assert len(results) == 1
        assert results[0].description == "Persistent lesson"

    def test_context_field_roundtrip(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        ctx = {"ma_trend": "up", "volume_ratio": 1.5}
        entry = mem.remember("lesson", "Context test", context=ctx, score=0.8)
        assert entry.context == ctx

    def test_entry_to_dict_contains_all_fields(self, tmp_store: Path):
        mem = ModuleLocalMemory("test_module", store_path=tmp_store)
        entry = mem.remember("lesson", "Test", symbol="000001", score=0.5)
        d = entry.to_dict()
        assert d["memory_id"]
        assert d["module_name"] == "test_module"
        assert d["memory_type"] == "lesson"
        assert d["description"] == "Test"
        assert d["symbol"] == "000001"
        assert d["score"] == 0.5
        assert d["timestamp"]
        assert d["access_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
