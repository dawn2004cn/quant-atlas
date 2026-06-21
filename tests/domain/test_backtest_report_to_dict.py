"""BacktestReport API serialization."""

from __future__ import annotations

from app.domain.entities import BacktestReport


def test_backtest_report_to_dict_flattens_metrics():
    report = BacktestReport(
        strategy="MA",
        symbol="600519",
        period={"start": "2024-01-01", "end": "2024-06-01"},
        metrics={
            "final_value": 110000.0,
            "total_return": 10.0,
            "annual_return": 12.0,
            "max_drawdown": 5.0,
            "sharpe": 1.2,
            "stock_data": {"dates": ["2024-01-01"], "closes": [100.0]},
            "equity_curve": [{"date": "2024-01-01", "value": 100000.0}],
        },
        trades=[{"date": "2024-01-02", "action": "buy", "price": 100.0}],
    )
    payload = report.to_dict()
    assert payload["symbol"] == "600519"
    assert payload["stock_data"]["closes"] == [100.0]
    assert payload["equity_curve"][0]["value"] == 100000.0
    assert payload["sharpe_ratio"] == 1.2
    assert payload["trades"][0]["action"] == "buy"
