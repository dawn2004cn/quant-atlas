from __future__ import annotations

from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.modules.market_data.services.cn_quote_snapshot import configure_cn_quote_snapshot
from app.modules.strategy.services.analytics.daily_workbench_service import DailyWorkbenchService


def test_build_limit_up_stocks_uses_snapshot_not_full_market_dump() -> None:
    market = MagicMock()
    market.list_quotes.side_effect = AssertionError("full-market list_quotes must not run")
    snap = configure_cn_quote_snapshot(market_service=market)
    snap.load_rows(
        [
            {"code": "000001", "name": "平安", "price": 10, "change_pct": 10.2},
            {"code": "600519", "name": "茅台", "price": 100, "change_pct": 1.0},
        ]
    )
    svc = DailyWorkbenchService(market_service=market, watchlist_service=MagicMock())
    rows = svc._build_limit_up_stocks(MarketCode.CN)
    assert rows
    assert rows[0]["code"] == "000001"
    market.list_quotes.assert_not_called()
