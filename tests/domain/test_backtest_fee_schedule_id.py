"""Fee schedule id appears on BacktestResult when configured."""

from app.domain.models.backtest_models import (
    BacktestConfig,
    BacktestEngine,
    StrategySignal,
    TradeDirection,
)


def test_backtest_engine_reports_fee_schedule_id():
    engine = BacktestEngine(BacktestConfig(fee_schedule_id="cn_a_retail_v1", slippage=0.0))
    result = engine.run(
        [StrategySignal(code="600519", direction=TradeDirection.LONG, strength=1.0)],
        {"600519": [100.0]},
    )
    assert result.fee_schedule_id == "cn_a_retail_v1"
    payload = result.to_dict()
    assert payload["fee_schedule_id"] == "cn_a_retail_v1"
    assert result.trades[0].commission >= 5.0
