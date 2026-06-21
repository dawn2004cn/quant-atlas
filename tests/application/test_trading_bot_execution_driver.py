from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.execution.services.trading_bot_service import TradingBotService
from app.infrastructure.execution.driver_registry import resolve_bot_execution_gateway
from app.infrastructure.execution.drivers.paper_driver import PaperExecutionDriver


def test_resolve_bot_gateway_picks_market_driver() -> None:
    gateway = resolve_bot_execution_gateway(
        {"symbols": ["AAPL"], "market": "US", "execution_mode": "paper"}
    )
    assert isinstance(gateway, PaperExecutionDriver)
    assert gateway.describe()["market"] == "US"


def test_trading_bot_service_uses_execution_gateway_factory() -> None:
    gateway = PaperExecutionDriver(market="CN", exchange="paper_cn")
    repo = MagicMock()
    repo.get_open_trades.return_value = []

    def strategy_factory(name: str) -> MagicMock:
        strat = MagicMock()
        strat.timeframe = "1h"
        strat.stoploss = -0.1
        strat.populate_indicators.side_effect = lambda df, _: df
        strat.populate_entry_trend.side_effect = lambda df, _: df
        return strat

    svc = TradingBotService(
        repository=repo,
        strategy_factory=strategy_factory,
        execution_gateway=gateway,
    )
    assert svc._resolve_gateway({}) is gateway
