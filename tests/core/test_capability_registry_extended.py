"""Extended regression tests for CapabilityRegistry + Bridge (Phase 5.1-5.2)."""

from __future__ import annotations

import pytest

from app.core.capability_bridge import (
    get_agent_capabilities,
    search_capabilities,
)
from app.core.capability_registry import (
    get_capability_registry,
    register_capability,
    reset_capability_registry,
)


class TestCapabilityRegistryCore:
    """Core registry functionality."""

    def setup_method(self):
        reset_capability_registry()

    def test_register_and_search_by_keyword(self):
        @register_capability(
            name="get_market_kline",
            description="Query A-share 5-minute kline data",
            domain="market_data",
            tags=["kline", "realtime"],
        )
        def get_kline(ticker: str, period: str = "5m"):
            return {"ticker": ticker, "bars": []}

        reg = get_capability_registry()
        assert reg.stats()["total"] == 1

        results = reg.search("kline")
        assert len(results) == 1
        assert results[0].name == "get_market_kline"

        results = reg.search("kline")
        assert len(results) == 1

    def test_search_by_domain_and_tags(self):
        @register_capability(name="calc_var", description="calculate value at risk", domain="risk", tags=["var", "portfolio"])
        def calc_var(pid: str): return {"var": 0.05}

        @register_capability(name="calc_vol", description="calculate portfolio volatility", domain="risk", tags=["vol", "portfolio"])
        def calc_vol(pid: str): return {"vol": 0.15}

        reg = get_capability_registry()
        risk_caps = reg.list_by_domain("risk")
        assert len(risk_caps) == 2

        results = reg.search("portfolio")
        assert len(results) == 2

    def test_resolve_and_execute(self):
        @register_capability(name="echo", description="echo input", domain="test", tags=[])
        def echo(x: str) -> str:
            return f"echo: {x}"

        reg = get_capability_registry()
        fn = reg.resolve("echo")
        assert fn is not None
        assert fn("hello") == "echo: hello"

    def test_to_agent_tools_schema(self):
        @register_capability(name="get_price", description="get latest price", domain="market", tags=["price"])
        def get_price(ticker: str) -> float:
            return 100.0

        reg = get_capability_registry()
        tools = reg.to_agent_tools()
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert "name" in tools[0]["function"]
        assert tools[0]["function"]["name"] == "get_price"
        assert "parameters" in tools[0]["function"]


class TestCapabilityBridge:
    """Bridge auto-registration and semantic search."""

    def setup_method(self):
        reset_capability_registry()

    def test_bridge_search_capabilities(self):
        @register_capability(name="get_kline", description="kline data", domain="market", tags=["kline"])
        def get_kline(ticker: str): return {}

        results = search_capabilities("kline")
        assert len(results) >= 1
        assert any("kline" in r["name"].lower() for r in results)

    def test_bridge_to_agent_tools(self):
        @register_capability(name="get_volume", description="get trading volume", domain="market", tags=["volume"])
        def get_volume(ticker: str) -> int: return 10000

        tools = get_agent_capabilities()
        assert len(tools) >= 1
        assert tools[0]["type"] == "function"


class TestCapabilityRegistryPersistence:
    """Registry state management."""

    def setup_method(self):
        reset_capability_registry()

    def test_reset_clears_all(self):
        @register_capability(name="temp", description="temp", domain="test", tags=[])
        def temp(): pass

        reg = get_capability_registry()
        assert reg.stats()["total"] == 1

        reset_capability_registry()
        reg = get_capability_registry()
        assert reg.stats()["total"] == 0


class TestCapabilityRegistryEdgeCases:
    """Edge cases and robustness."""

    def setup_method(self):
        reset_capability_registry()

    def test_duplicate_name_overwrites(self):
        @register_capability(name="dup", description="first", domain="test", tags=[])
        def first(): return 1

        @register_capability(name="dup", description="second", domain="test", tags=[])
        def second(): return 2

        reg = get_capability_registry()
        assert reg.stats()["total"] == 1
        assert reg.resolve("dup")() == 2

    def test_search_empty_query_returns_all(self):
        @register_capability(name="a", description="a", domain="d1", tags=[])
        def a(): pass
        @register_capability(name="b", description="b", domain="d2", tags=[])
        def b(): pass

        reg = get_capability_registry()
        results = reg.search("")
        assert len(results) == 2

    def test_matches_query_scoring(self):
        from app.core.capability_registry import Capability
        cap = Capability(name="test_cap", description="This is a test capability", domain="test", tags=["tag1", "tag2"])
        assert cap.matches_query("test") > 0
        assert cap.matches_query("capability") > 0
        assert cap.matches_query("tag1") > 0
        assert cap.matches_query("nonexistent") == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
