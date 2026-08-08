"""Paper pool promote writes real tournament metrics."""

from __future__ import annotations

from app.domain.alpha.paper_trading import PaperTradingScheduler
from app.modules.strategy.services.tournament.paper_pool_adapter import PaperTradingPoolAdapter


def test_promote_writes_sharpe_mdd_not_zero_return_only():
    scheduler = PaperTradingScheduler()
    pool = PaperTradingPoolAdapter(scheduler=scheduler)
    pool.promote(
        "nl.metrics",
        reason="gates_ok",
        metrics={
            "sharpe": 2.1,
            "max_drawdown": 0.08,
            "win_rate": 0.55,
            "sample_start": "2023-01-01",
            "sample_end": "2024-12-31",
            "total_return": 0.42,
        },
    )
    account = scheduler.get_account("nl.metrics")
    assert account is not None
    result = account._backtest_result  # noqa: SLF001
    assert result is not None
    assert float(result.get("sharpe") or 0) == 2.1
    assert float(result.get("max_drawdown") or 0) == 0.08
    assert float(result.get("total_return") or 0) == 0.42
