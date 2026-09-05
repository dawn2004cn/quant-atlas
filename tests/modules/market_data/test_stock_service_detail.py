from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.domain.enums import MarketCode
from app.modules.market_data.services.cn_quote_book import clear_cn_quote_book, save_cn_quote_book
from app.modules.market_data.services.stock_service import StockApplicationService


def test_get_stock_detail_uses_redis_book_without_live_quote() -> None:
    clear_cn_quote_book()
    save_cn_quote_book(
        [{"code": "000001", "name": "平安银行", "price": 12.3, "change_pct": 1.1, "amount": 1e8}],
        source="test",
    )
    provider = MagicMock()
    provider.get_realtime_quotes.side_effect = AssertionError("page path must read Redis book")
    provider.get_stock_history.side_effect = AssertionError("must not pull live history")
    svc = StockApplicationService(market_provider=provider)
    result = svc.get_stock_detail("000001", MarketCode.CN)
    assert result.profile["realtime"]["price"] == 12.3
    assert result.profile["name"] == "平安银行"
    clear_cn_quote_book()


def test_get_stock_detail_skips_live_history() -> None:
    clear_cn_quote_book()
    quote = SimpleNamespace(
        code="000001",
        name="平安银行",
        price=10.0,
        change_amount=0.1,
        change_pct=1.0,
        volume=100,
        amount=200,
        turnover=0,
        pe=None,
        pb=None,
        total_market_cap=0,
        industry="",
        open_price=0,
        high_price=0,
        low_price=0,
        prev_close=0,
        volume_ratio=0,
        amplitude=0,
    )
    cache = MagicMock()
    cache.get_stocks_by_codes.return_value = []
    cache.get_stock_history_for_code.return_value = []
    provider = MagicMock()
    provider.get_realtime_quotes.return_value = [quote]
    provider.get_stock_history.side_effect = AssertionError("must not pull live history")
    svc = StockApplicationService(
        market_provider=provider,
        stock_cache=cache,
        indicator_provider=MagicMock(),
    )
    result = svc.get_stock_detail("000001", MarketCode.CN)
    assert result.profile["realtime"]["price"] == 10.0
    assert result.indicators == {}
    provider.get_stock_history.assert_not_called()
