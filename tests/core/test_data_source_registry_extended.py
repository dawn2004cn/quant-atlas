"""Extended regression tests for DataSourceRegistry (Phase 7.1-7.2)."""

from __future__ import annotations

import pytest

from app.core.data_source_registry import (
    DataSource,
    data_source,
    get_data_source_registry,
    reset_data_source_registry,
)


class TestDataSourceRegistry:
    """Semantic data source discovery."""

    def setup_method(self):
        reset_data_source_registry()

    def test_register_and_find_by_type(self):
        reg = get_data_source_registry()
        reg.register(DataSource(
            name="akshare_kline",
            type="kline",
            scope="history",
            market="CN",
            priority=10,
        ))
        reg.register(DataSource(
            name="yfinance_kline",
            type="kline",
            scope="history",
            market="US",
            priority=5,
        ))

        cn_sources = reg.find(type="kline", market="CN")
        assert len(cn_sources) == 1
        assert cn_sources[0].name == "akshare_kline"

        all_kline = reg.find(type="kline")
        assert len(all_kline) == 2

    def test_priority_ordering(self):
        reg = get_data_source_registry()
        reg.register(DataSource(name="low_pri", type="quote", scope="realtime", priority=1))
        reg.register(DataSource(name="high_pri", type="quote", scope="realtime", priority=100))

        results = reg.find(type="quote")
        assert results[0].name == "high_pri"

    def test_find_best_returns_highest_priority(self):
        reg = get_data_source_registry()
        reg.register(DataSource(name="slow", type="kline", scope="history", priority=1))
        reg.register(DataSource(name="fast", type="kline", scope="history", priority=50))

        best = reg.find_best(type="kline", scope="history")
        assert best is not None
        assert best.name == "fast"

    def test_find_best_returns_none_if_no_match(self):
        reg = get_data_source_registry()
        best = reg.find_best(type="nonexistent")
        assert best is None

    def test_find_market_hk(self):
        reg = get_data_source_registry()
        reg.register(DataSource(name="hk_quote", type="quote", scope="realtime", market="HK"))
        results = reg.find(type="quote", market="HK")
        assert len(results) == 1

    def test_thread_safety(self):
        import threading
        reg = get_data_source_registry()
        errors = []

        def register_sources():
            try:
                for i in range(50):
                    reg.register(DataSource(name=f"src_{i}", type="kline", scope="history"))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_sources) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(reg.find(type="kline")) == 4 * 50

    def test_decorator_registration(self):
        @data_source(name="decorated_source", type="fundamental", scope="history", market="CN")
        def fetch_fundamentals(ticker: str):
            return {"pe": 15.0}

        reg = get_data_source_registry()
        results = reg.find(type="fundamental")
        assert len(results) == 1
        assert results[0].name == "decorated_source"
        assert results[0].provider is not None
        assert results[0].provider("000001")["pe"] == 15.0

    def test_matches_method(self):
        src = DataSource(name="test", type="kline", scope="history", market="CN")
        assert src.matches(type="kline")
        assert src.matches(type="kline", scope="history")
        assert src.matches(type="kline", scope="history", market="CN")
        assert not src.matches(type="quote")
        assert not src.matches(type="kline", scope="realtime")
        assert not src.matches(type="kline", market="US")

    def test_find_returns_empty_list_for_no_match(self):
        reg = get_data_source_registry()
        results = reg.find(type="nonexistent")
        assert results == []

    def test_tag_field(self):
        src = DataSource(name="tagged", type="news", scope="realtime", tags=("breaking", "headlines"))
        assert "breaking" in src.tags
        assert "headlines" in src.tags


class TestDataSourceRegistryReset:
    """Registry isolation."""

    def test_reset_clears_state(self):
        reset_data_source_registry()
        reg = get_data_source_registry()
        reg.register(DataSource(name="temp", type="kline", scope="history"))
        assert len(reg.find(type="kline")) == 1

        reset_data_source_registry()
        assert len(get_data_source_registry().find(type="kline")) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
