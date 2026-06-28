"""Regression tests for GlobalStateBus (Phase 12.3) and MemoryFabric (Phase 12.1)."""

from __future__ import annotations

import pytest

from app.core.mesh.global_state_bus import GlobalStateBus, get_global_state_bus


class TestGlobalStateBus:
    """Near-Memory Mesh — shared state bus."""

    def setup_method(self):
        # Fresh instance for each test
        self.bus = GlobalStateBus()

    def test_write_and_read_state(self):
        self.bus.write_state("market_data", {"confidence": 0.85, "risk_level": 0.3})
        state = self.bus.read_state("market_data")
        assert state is not None
        assert state["confidence"] == 0.85
        assert state["risk_level"] == 0.3
        assert "timestamp" in state

    def test_read_nonexistent_module(self):
        state = self.bus.read_state("nonexistent_module")
        assert state is None

    def test_read_all_states_returns_snapshot(self):
        self.bus.write_state("module_a", {"confidence": 0.9})
        self.bus.write_state("module_b", {"confidence": 0.7, "risk_level": 0.5})
        all_states = self.bus.read_all_states()
        assert "module_a" in all_states
        assert "module_b" in all_states
        assert all_states["module_a"]["confidence"] == 0.9

    def test_read_all_states_is_independent_copy(self):
        self.bus.write_state("mod1", {"confidence": 0.5})
        snapshot = self.bus.read_all_states()
        self.bus.write_state("mod1", {"confidence": 1.0})
        assert snapshot["mod1"]["confidence"] == 0.5

    def test_version_increments_on_write(self):
        v0 = self.bus.get_version()
        self.bus.write_state("mod", {"confidence": 0.5})
        v1 = self.bus.get_version()
        assert v1 > v0

    def test_write_preserves_extra_fields(self):
        self.bus.write_state("mod", {"confidence": 0.8, "risk_level": 0.2, "custom_field": "value"})
        state = self.bus.read_state("mod")
        assert state["custom_field"] == "value"
        assert state["confidence"] == 0.8

    def test_singleton_get_global_state_bus(self):
        bus1 = get_global_state_bus()
        bus2 = get_global_state_bus()
        assert bus1 is bus2
        # Cleanup for other tests
        import app.core.mesh.global_state_bus as gsb
        gsb._global_bus = None

    def test_missing_extra_fields_get_defaults(self):
        self.bus.write_state("mod", {"confidence": 0.5})
        state = self.bus.read_state("mod")
        assert "risk_level" in state
        assert state["risk_level"] == 0.0


DEFAULT_VERDICT = {
    "symbol": "600519",
    "market": "CN",
    "meta_verdict": "bullish",
    "meta_confidence": 0.85,
    "team_count": 5,
}


class TestMemoryFabric:
    """Associative vector store for ArbiterVerdict indexing."""

    def setup_method(self):
        from app.core.mesh.memory_fabric import MemoryFabric
        self.fabric = MemoryFabric(dimensions=64)

    def test_index_verdict(self):
        entry_id = self.fabric.index_verdict(DEFAULT_VERDICT)
        assert entry_id.startswith("mem-")
        assert len(self.fabric._entries) == 1

    def test_index_verdict_with_feedback(self):
        entry_id = self.fabric.index_verdict(DEFAULT_VERDICT, feedback="confirmed by analyst")
        assert entry_id is not None
        entry = self.fabric._entries[entry_id]
        assert "feedback" in entry.content

    def test_semantic_search_returns_relevant_results(self):
        self.fabric.index_verdict({"symbol": "AAPL", "market": "US", "meta_verdict": "bullish", "meta_confidence": 0.9, "team_count": 3})
        self.fabric.index_verdict({"symbol": "TSLA", "market": "US", "meta_verdict": "bearish", "meta_confidence": 0.6, "team_count": 4})
        results = self.fabric.semantic_search("bullish AAPL", top_k=1)
        assert len(results) >= 1
        assert results[0].metadata["symbol"] == "AAPL"

    def test_semantic_search_empty(self):
        results = self.fabric.semantic_search("anything", top_k=5)
        assert results == []

    def test_index_user_feedback(self):
        eid = self.fabric.index_user_feedback(user_id=42, feedback={"rating": 5, "comment": "good"})
        assert eid is not None
        entry = self.fabric._entries[eid]
        assert entry.metadata["user_id"] == "42"

    def test_get_stats(self):
        self.fabric.index_verdict(DEFAULT_VERDICT)
        self.fabric.index_verdict({"symbol": "AAPL", "market": "US", "meta_verdict": "neutral", "meta_confidence": 0.5, "team_count": 2})
        stats = self.fabric.get_stats()
        assert stats["total_entries"] == 2
        assert stats["dimensions"] == 64

    def test_recall_by_type(self):
        self.fabric.index_verdict(DEFAULT_VERDICT)
        self.fabric.index_verdict({"symbol": "000001", "market": "CN", "meta_verdict": "bearish", "meta_confidence": 0.3, "team_count": 2})
        results = self.fabric.recall_by_type("bullish")
        assert len(results) >= 1
        assert all(r.metadata["verdict_type"] == "bullish" for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
