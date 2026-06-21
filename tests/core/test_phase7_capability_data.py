"""Tests for Phase 5 (CapabilityRegistry) and Phase 7 (DataSourceRegistry) components."""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# ── CapabilityRegistry ──────────────────────────────────────────────────


def test_capability_registry_register_and_search():
    from app.core.capability_registry import (
        CapabilityRegistry,
        get_capability_registry,
        reset_capability_registry,
        register_capability,
    )

    reset_capability_registry()

    @register_capability(name="get_kline", description="query A-share 5-min kline data", domain="market_data",
                         tags=["kline", "realtime"])
    def get_kline(ticker, period="5m"):
        return {"ticker": ticker, "bars": []}

    @register_capability(name="calc_vol", description="calculate portfolio volatility", domain="portfolio",
                         tags=["risk", "volatility"])
    def calc_vol(pid):
        return {"vol": 0.15}

    reg = get_capability_registry()
    assert reg.stats()["total"] == 2

    results = reg.search("kline")
    assert len(results) == 1
    assert results[0].name == "get_kline"

    results = reg.search("volatility")
    assert len(results) == 1
    assert results[0].name == "calc_vol"

    results = reg.search("nonexistent")
    assert len(results) == 0

    tools = reg.to_agent_tools()
    assert len(tools) == 2
    assert tools[0]["type"] == "function"

    fn = reg.resolve("get_kline")
    assert fn is not None
    assert fn("000001")["ticker"] == "000001"


def test_capability_registry_by_domain():
    from app.core.capability_registry import get_capability_registry
    reg = get_capability_registry()
    market_caps = reg.list_by_domain("market_data")
    assert len(market_caps) >= 1
    assert all(c.domain == "market_data" for c in market_caps)


def test_capability_bridge_search():
    from app.core.capability_bridge import search_capabilities
    from app.core.capability_registry import get_capability_registry
    results = search_capabilities("kline")
    assert len(results) >= 1
    assert any("kline" in r["name"] or "kline" in r["description"].lower() for r in results)


# ── DataSourceRegistry ──────────────────────────────────────────────────


def test_data_source_registry_register_and_find():
    from app.core.data_source_registry import (
        DataSourceRegistry,
        DataSource,
        get_data_source_registry,
        reset_data_source_registry,
        data_source,
    )

    reset_data_source_registry()

    reg = get_data_source_registry()
    reg.register(DataSource(name="tencent", type="quote", scope="realtime", market="CN", priority=90))
    reg.register(DataSource(name="tdx", type="kline", scope="history", market="CN", priority=90))
    reg.register(DataSource(name="akshare", type="kline", scope="history", market="CN", priority=70))
    reg.register(DataSource(name="yfinance_us", type="quote", scope="realtime", market="US", priority=80))

    assert reg.stats()["total"] == 4

    sources = reg.find(type="kline", scope="history", market="CN")
    assert len(sources) == 2
    assert sources[0].name == "tdx"  # Higher priority first
    assert sources[1].name == "akshare"

    best = reg.find_best(type="quote", scope="realtime", market="US")
    assert best is not None
    assert best.name == "yfinance_us"

    all_types = reg.list_types()
    assert "kline" in all_types
    assert "quote" in all_types


def test_data_source_registry_by_domain():
    from app.core.data_source_registry import get_data_source_registry
    reg = get_data_source_registry()
    cn_sources = reg.find(market="CN")
    assert len(cn_sources) >= 3


def test_data_source_registry_no_match():
    from app.core.data_source_registry import get_data_source_registry
    reg = get_data_source_registry()
    sources = reg.find(type="nonexistent")
    assert len(sources) == 0

    best = reg.find_best(type="nonexistent", scope="realtime")
    assert best is None


def test_data_source_decorator():
    from app.core.data_source_registry import data_source, get_data_source_registry

    @data_source(name="custom_fn", type="indicator", scope="realtime", market="CN", priority=50)
    def my_custom_fn():
        pass

    reg = get_data_source_registry()
    best = reg.find_best(type="indicator", scope="realtime")
    assert best is not None
    assert best.name == "custom_fn"
    assert best.provider is my_custom_fn


def test_find_data_source_convenience():
    from app.core.data_source_registry import find_data_source
    src = find_data_source("quote", scope="realtime", market="CN")
    assert src is not None
    assert src.type == "quote"


# ── DecisionReviewQueue ─────────────────────────────────────────────────


@pytest.fixture
def review_queue():
    from app.modules.system.services.ui.decision_review_queue import DecisionReviewQueue
    tmp = Path(tempfile.mkdtemp()) / "queue.json"
    q = DecisionReviewQueue(store_path=tmp)
    yield q
    if tmp.exists():
        tmp.unlink()


def test_review_queue_enqueue_and_list(review_queue):
    from app.modules.system.services.ui.decision_review_queue import ReviewStatus

    d = review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="low_confidence")
    assert d.decision_id == "dec_001"
    assert d.status == ReviewStatus.PENDING
    assert d.confidence == 0.45
    assert "low_confidence" in d.reason

    pending = review_queue.list_pending()
    assert len(pending) == 1


def test_review_queue_no_duplicate(review_queue):
    d1 = review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="low_confidence")
    d2 = review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="low_confidence")
    assert d1.decision_id == d2.decision_id


def test_review_queue_approve(review_queue):
    from app.modules.system.services.ui.decision_review_queue import ReviewStatus

    review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="low_confidence")
    approved = review_queue.approve("dec_001")
    assert approved is not None
    assert approved.status == ReviewStatus.APPROVED

    stats = review_queue.stats()
    assert stats["by_status"].get("approved", 0) == 1


def test_review_queue_reject(review_queue):
    from app.modules.system.services.ui.decision_review_queue import ReviewStatus

    review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="test")
    rejected = review_queue.reject("dec_001")
    assert rejected is not None
    assert rejected.status == ReviewStatus.REJECTED


def test_review_queue_add_correction(review_queue):
    review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="test")
    corr = review_queue.add_correction(
        decision_id="dec_001",
        user_id=1,
        target_phase="news",
        action="ignore_evidence",
        comment="this news item is outdated",
    )
    # Should work even if decision was already approved
    assert corr is not None
    assert corr.action == "ignore_evidence"
    assert corr.target_phase == "news"

    # Decision should now be CORRECTED status
    dec = review_queue.get_pending("dec_001")
    from app.modules.system.services.ui.decision_review_queue import ReviewStatus
    assert dec.status == ReviewStatus.CORRECTED


def test_review_queue_correction_nonexistent(review_queue):
    corr = review_queue.add_correction(
        decision_id="nonexistent",
        user_id=1,
        target_phase="x",
        action="x",
    )
    assert corr is None


def test_review_queue_get_pending(review_queue):
    review_queue.enqueue(decision_id="dec_001", subject="CN:000001", confidence=0.45, reason="test")
    dec = review_queue.get_pending("dec_001")
    assert dec is not None
    assert dec.decision_id == "dec_001"

    dec2 = review_queue.get_pending("nonexistent")
    assert dec2 is None


def test_review_queue_stats(review_queue):
    review_queue.enqueue(decision_id="dec_001", subject="A", confidence=0.3, reason="first")
    review_queue.enqueue(decision_id="dec_002", subject="B", confidence=0.4, reason="second")
    review_queue.approve("dec_001")

    stats = review_queue.stats()
    assert stats["total"] == 2
    assert stats["by_status"].get("pending", 0) == 1
    assert stats["by_status"].get("approved", 0) == 1


def test_review_queue_list_pending_limit(review_queue):
    for i in range(10):
        review_queue.enqueue(decision_id=f"dec_{i:03d}", subject=f"subject_{i}", confidence=0.5, reason="test")

    pending = review_queue.list_pending(limit=3)
    assert len(pending) <= 3


# ── EventBus MarketRegimeChangedEvent ───────────────────────────────────


def test_market_regime_changed_event():
    from app.core.event_bus import get_event_bus, MarketRegimeChangedEvent, EventBus

    bus = get_event_bus()
    caught = []

    def handler(event):
        caught.append(event)

    bus.subscribe(MarketRegimeChangedEvent, handler)

    bus.publish(MarketRegimeChangedEvent(
        previous_regime="bear",
        new_regime="bull",
        market="CN",
        confidence=0.85,
        trigger_reason="ma_crossover",
        source="test",
    ))

    assert len(caught) == 1
    e = caught[0]
    assert e.previous_regime == "bear"
    assert e.new_regime == "bull"
    assert e.confidence == 0.85
    assert e.trigger_reason == "ma_crossover"
    assert e.market == "CN"
    assert e.source == "test"


def test_market_regime_changed_event_no_handler_match():
    from app.core.event_bus import get_event_bus, MarketRegimeChangedEvent, ServiceStartedEvent
    bus = get_event_bus()
    caught = []

    def handler(event):
        caught.append(event)

    # Subscribe to ServiceStartedEvent, publish MarketRegimeChangedEvent
    bus.subscribe(ServiceStartedEvent, handler)
    bus.publish(MarketRegimeChangedEvent(
        previous_regime="bull",
        new_regime="bear",
        market="CN",
        confidence=0.5,
        trigger_reason="test",
        source="test",
    ))

    # Handler should NOT be called (different event type)
    assert len(caught) == 0
