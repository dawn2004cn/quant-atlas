from __future__ import annotations

from app.domain.dto.analytics_dto import AttributionReportDTO, FactorContributionDTO, MarketEffectDTO
from app.modules.execution.services.trade_outcome_review_service import TradeOutcomeReviewService


class _AttributionService:
    def __init__(self, return_pct: float = 1.2) -> None:
        self.return_pct = return_pct
        self.calls = []

    def build_report(self, **kwargs):
        self.calls.append(kwargs)
        return AttributionReportDTO(
            strategy_name=kwargs["strategy_name"],
            period=kwargs["period"],
            symbol=kwargs["symbol"],
            total_return=self.return_pct,
            market_effect=MarketEffectDTO(market_return=0.2, alpha=1.0),
            factors=[FactorContributionDTO(factor_name="entry_timing", contribution_pct=self.return_pct, contribution_amount=1.0)],
        )


def test_record_close_and_review_card(tmp_path) -> None:
    attribution = _AttributionService()
    service = TradeOutcomeReviewService(store_path=tmp_path / "reviews.json", attribution_service=attribution)

    trade = service.record_trade(
        trade_id="t1",
        user_id=1,
        symbol="600519",
        direction="buy",
        entry_price=100,
        quantity=10,
    )
    closed = service.close_trade(trade_id="t1", exit_price=110)

    assert closed is not None
    assert closed.pnl == 100.0
    assert closed.pnl_pct == 10.0
    review = service.get_review("t1")
    assert review is not None
    assert review.summary.startswith("600519 buy")
    assert review.pnl == 100.0
    assert review.attribution is not None
    assert attribution.calls[0]["symbol"] == "600519"


def test_close_missing_trade_returns_none(tmp_path) -> None:
    service = TradeOutcomeReviewService(store_path=tmp_path / "reviews.json")

    assert service.close_trade(trade_id="missing", exit_price=10) is None


def test_list_pending_reviews_limits_and_sorts(tmp_path) -> None:
    service = TradeOutcomeReviewService(store_path=tmp_path / "reviews.json")
    service.record_trade(trade_id="t1", user_id=1, symbol="000001", direction="buy", entry_price=10, quantity=1)
    service.close_trade(trade_id="t1", exit_price=11)
    service.record_trade(trade_id="t2", user_id=1, symbol="000002", direction="buy", entry_price=10, quantity=1)
    service.close_trade(trade_id="t2", exit_price=9)

    assert [review.trade_id for review in service.list_pending_reviews(limit=1)] == ["t2"]
