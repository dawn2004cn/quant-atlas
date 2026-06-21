"""Unit tests for TradeOutcomeReviewService — post-trade review loop.

Covers app/modules/execution/services/trade_outcome_review_service.py:
- record_trade (happy path, idempotent duplicate)
- close_trade (PnL, review card generation, already-closed guard)
- get_review / list_pending_reviews
- persistence round-trip via JSON store
- winning / losing / breakeven key_lesson branches
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.domain.dto.analytics_dto import AttributionReportDTO, MarketEffectDTO
from app.modules.execution.services.trade_outcome_review_service import (
    TradeOutcomeReviewService,
    get_trade_review_service,
)


def _attribution_stub(**_kwargs: object) -> AttributionReportDTO:
    return AttributionReportDTO(
        strategy_name="manual",
        period="3d",
        total_return=5.0,
        market_effect=MarketEffectDTO(market_return=1.0, alpha=4.0),
        summary="stub attribution",
    )


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "trade_reviews.json"


@pytest.fixture
def service(store_path) -> TradeOutcomeReviewService:
    attribution = SimpleNamespace(build_report=_attribution_stub)
    return TradeOutcomeReviewService(store_path=store_path, attribution_service=attribution)


def test_record_trade_persists_and_normalizes_symbol(service: TradeOutcomeReviewService, store_path):
    rec = service.record_trade(
        trade_id="t-001",
        user_id=1,
        symbol=" 600000 ",
        direction="buy",
        entry_price=10.0,
        quantity=100,
    )
    assert rec.symbol == "600000"
    assert rec.review_status == "pending"
    assert store_path.exists()


def test_record_trade_idempotent(service: TradeOutcomeReviewService):
    first = service.record_trade(
        trade_id="t-dup",
        user_id=1,
        symbol="600000",
        direction="buy",
        entry_price=10.0,
        quantity=50,
    )
    second = service.record_trade(
        trade_id="t-dup",
        user_id=99,
        symbol="000001",
        direction="sell",
        entry_price=20.0,
        quantity=1,
    )
    assert second is first
    assert second.user_id == 1
    assert second.symbol == "600000"


def test_close_trade_computes_pnl_and_review(service: TradeOutcomeReviewService):
    service.record_trade(
        trade_id="t-win",
        user_id=1,
        symbol="600519",
        direction="buy",
        entry_price=100.0,
        quantity=10,
    )
    closed = service.close_trade(trade_id="t-win", exit_price=110.0)
    assert closed is not None
    assert closed.pnl == pytest.approx(100.0)
    assert closed.pnl_pct == pytest.approx(10.0)
    assert closed.review_status == "reviewed"

    review = service.get_review("t-win")
    assert review is not None
    assert review.pnl == pytest.approx(100.0)
    assert "赚钱" in review.key_lesson
    assert review.summary
    assert review.attribution is not None


def test_close_trade_loss_key_lesson(service: TradeOutcomeReviewService):
    service.record_trade(
        trade_id="t-loss",
        user_id=1,
        symbol="000001",
        direction="buy",
        entry_price=50.0,
        quantity=20,
    )
    service.close_trade(trade_id="t-loss", exit_price=45.0)
    review = service.get_review("t-loss")
    assert review is not None
    assert review.pnl == pytest.approx(-100.0)
    assert "亏钱" in review.key_lesson


def test_close_trade_breakeven_key_lesson(service: TradeOutcomeReviewService):
    service.record_trade(
        trade_id="t-flat",
        user_id=1,
        symbol="600000",
        direction="buy",
        entry_price=10.0,
        quantity=100,
    )
    service.close_trade(trade_id="t-flat", exit_price=10.0)
    review = service.get_review("t-flat")
    assert review is not None
    assert review.pnl == pytest.approx(0.0)
    assert "无盈亏" in review.key_lesson


def test_close_trade_missing_returns_none(service: TradeOutcomeReviewService):
    assert service.close_trade(trade_id="missing", exit_price=1.0) is None


def test_close_trade_already_closed_is_idempotent(service: TradeOutcomeReviewService):
    service.record_trade(
        trade_id="t-once",
        user_id=1,
        symbol="600000",
        direction="buy",
        entry_price=10.0,
        quantity=10,
    )
    first = service.close_trade(trade_id="t-once", exit_price=12.0)
    second = service.close_trade(trade_id="t-once", exit_price=99.0)
    assert second is first
    assert second.exit_price == pytest.approx(12.0)


def test_list_pending_reviews_sorted(service: TradeOutcomeReviewService):
    for tid, exit_px in (("a", 11.0), ("b", 9.0)):
        service.record_trade(
            trade_id=tid,
            user_id=1,
            symbol="600000",
            direction="buy",
            entry_price=10.0,
            quantity=10,
        )
        service.close_trade(trade_id=tid, exit_price=exit_px)
    items = service.list_pending_reviews(limit=10)
    assert len(items) == 2
    assert items[0].generated_at >= items[1].generated_at


def test_persistence_round_trip(store_path):
    svc1 = TradeOutcomeReviewService(store_path=store_path, attribution_service=SimpleNamespace())
    svc1.record_trade(
        trade_id="persist-1",
        user_id=7,
        symbol="600000",
        direction="buy",
        entry_price=8.0,
        quantity=50,
    )
    svc1.close_trade(trade_id="persist-1", exit_price=9.0)

    svc2 = TradeOutcomeReviewService(store_path=store_path, attribution_service=SimpleNamespace())
    assert "persist-1" in svc2._trades
    assert svc2.get_review("persist-1") is not None


def test_get_trade_review_service_singleton():
    svc_a = get_trade_review_service()
    svc_b = get_trade_review_service()
    assert svc_a is svc_b
