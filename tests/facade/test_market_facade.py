from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.application.errors import ValidationError
from app.domain.enums import MarketCode
from app.facade.market_facade import MarketFacade


class _PanoramaStub:
    def __init__(self, payload: dict):
        self._payload = payload

    def model_dump(self) -> dict:
        return self._payload


def test_get_panorama_delegates_to_market_service():
    market_service = MagicMock()
    market_service.get_panorama.return_value = _PanoramaStub(
        {"market_status": "active", "sentiment_score": 0.5}
    )
    facade = MarketFacade(
        stock_service=MagicMock(),
        market_service=market_service,
    )

    result = facade.get_panorama("CN")

    assert result["market_status"] == "active"
    market_service.get_panorama.assert_called_once_with(MarketCode.CN)


def test_get_panorama_invalid_market_raises():
    facade = MarketFacade(stock_service=MagicMock(), market_service=MagicMock())

    with pytest.raises(ValidationError, match="Invalid market"):
        facade.get_panorama("NOT_A_MARKET")


def test_get_panorama_falls_back_to_stock_service():
    stock_service = MagicMock()
    stock_service.get_panorama.return_value = {"market": "CN", "items": []}
    facade = MarketFacade(stock_service=stock_service, market_service=None)

    result = facade.get_panorama(MarketCode.CN)

    assert result["market"] == "CN"
    stock_service.get_panorama.assert_called_once_with(MarketCode.CN)


def test_api_v2_context_dataclass_field_order():
    """Regression: optional fields must not precede required fields."""
    from app.presentation.api.v2_context import ApiV2Context

    fields = list(ApiV2Context.__dataclass_fields__)
    assert fields.index("market_facade") > fields.index("stock_service")
    assert fields.index("market_facade") > fields.index("task_message_store")
    assert fields.index("backtest_facade") > fields.index("task_message_store")
    assert fields.index("ai_facade") > fields.index("task_message_store")


def test_get_history_bars_rejects_invalid_date_range():
    facade = MarketFacade(stock_service=MagicMock(), market_service=MagicMock())

    with pytest.raises(ValidationError, match="start_date"):
        facade.get_history_bars(
            symbol="600519",
            market="CN",
            start_date="2024-06-01",
            end_date="2024-01-01",
        )


def test_get_history_bars_rejects_bad_date_format():
    facade = MarketFacade(stock_service=MagicMock(), market_service=MagicMock())

    with pytest.raises(ValidationError, match="YYYY-MM-DD"):
        facade.get_history_bars(
            symbol="600519",
            market="CN",
            start_date="2024/01/01",
        )


def test_list_quotes_normalizes_symbols():
    stock_service = MagicMock()
    stock_service.list_quotes.return_value = []
    facade = MarketFacade(stock_service=stock_service, market_service=MagicMock())

    facade.list_quotes("CN", symbols=[" 600519 ", ""])

    stock_service.list_quotes.assert_called_once_with("CN", ["600519"])


def test_observe_facade_records_without_prometheus():
    from app.facade._helpers import observe_facade

    with observe_facade("market", "noop"):
        assert True


def test_get_history_bars_uses_get_history_fallback():
    class _MarketSvc:
        def get_history(self, symbol, market, start="", end=""):
            return [
                {"date": "2024-01-01", "close": 10.0},
                {"date": "2024-01-02", "close": 11.0},
            ]

    market_service = _MarketSvc()
    facade = MarketFacade(stock_service=MagicMock(), market_service=market_service)

    bars = facade.get_history_bars(
        symbol="600519",
        market="CN",
        start_date="2024-01-01",
        end_date="2024-01-02",
    )

    assert len(bars) == 2
