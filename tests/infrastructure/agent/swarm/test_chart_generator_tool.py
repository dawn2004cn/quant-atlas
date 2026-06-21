"""Chart generator uses market data when available."""

from __future__ import annotations

from unittest.mock import patch

from app.infrastructure.agent.swarm.tools.chart_generator_tool import (
    ChartGeneratorTool,
    _bars_to_ohlcv_df,
)


def test_bars_to_ohlcv_df_shapes_columns() -> None:
    bars = [
        {"date": "2024-01-02", "open": 10, "high": 11, "low": 9, "close": 10.5, "volume": 1000},
        {"date": "2024-01-03", "open": 10.5, "high": 12, "low": 10, "close": 11.5, "volume": 1200},
    ]
    df = _bars_to_ohlcv_df(bars)
    assert len(df) == 2
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]


def test_chart_generator_reports_no_data() -> None:
    tool = ChartGeneratorTool()
    with patch(
        "app.infrastructure.agent.swarm.tools.chart_generator_tool._load_symbol_ohlcv",
        return_value=None,
    ):
        msg = tool.execute(symbol="600519", filename="x.png", run_dir=".")
    assert "no market data" in msg
