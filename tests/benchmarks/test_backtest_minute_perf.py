"""SRS D6: minute-bar backtest baseline + vectorized 10y-scale run.

Does NOT claim ≤10s unless the artifact elapsed_s is actually under 10.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.domain.backtest.minute_engine import (
    TEN_YEAR_MINUTE_BARS,
    run_minute_backtest,
    square_wave_signal,
    synthetic_minute_closes,
)
from app.domain.models.backtest_models import (
    BacktestConfig,
    BacktestEngine,
    StrategySignal,
    TradeDirection,
)


def _toy_engine_20k() -> dict:
    closes = [100.0 + ((i % 17) - 8) * 0.01 for i in range(20_000)]
    signals = [
        StrategySignal(code="SYN", direction=TradeDirection.LONG, strength=1.0)
        for _ in range(0, len(closes), 500)
    ]
    engine = BacktestEngine(
        BacktestConfig(initial_capital=1_000_000.0, fee_schedule_id="cn_a_retail_v1", slippage=0.0),
    )
    import time

    t0 = time.perf_counter()
    result = engine.run(signals, {"SYN": closes})
    elapsed = time.perf_counter() - t0
    assert result.fee_schedule_id == "cn_a_retail_v1"
    assert len(result.trades) == len(signals)
    assert elapsed < 5.0
    return {"bars": len(closes), "trades": len(result.trades), "elapsed_s": round(elapsed, 6)}


def test_minute_backtest_baseline_completes_with_fee_schedule():
    toy = _toy_engine_20k()
    closes = synthetic_minute_closes(20_000)
    sig = square_wave_signal(20_000, period=500)
    vec0 = run_minute_backtest(closes, sig, fee_schedule_id=None, mode="vectorized")
    loop0 = run_minute_backtest(closes, sig, fee_schedule_id=None, mode="loop")
    assert vec0.n_trades == loop0.n_trades
    assert abs(vec0.total_return - loop0.total_return) < 1e-9
    vec = run_minute_backtest(closes, sig, mode="vectorized")
    loop = run_minute_backtest(closes, sig, mode="loop")
    assert vec.n_trades == loop.n_trades
    assert vec.n_bars == 20_000
    assert vec.elapsed_s < 2.0
    out = {
        "toy_engine": toy,
        "vectorized_20k": vec.as_dict(),
        "loop_20k": loop.as_dict(),
        "note": "synthetic; SRS 10y-minute ≤10s not claimed here",
    }
    artifact = Path("instance") / "backtest_minute_baseline.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


def test_ten_year_minute_vectorized_records_slo():
    n = TEN_YEAR_MINUTE_BARS
    closes = synthetic_minute_closes(n)
    sig = square_wave_signal(n, period=480)
    result = run_minute_backtest(closes, sig, mode="vectorized")
    assert result.n_bars == n
    assert result.n_trades > 0
    artifact = Path("instance") / "backtest_minute_10y_vectorized.json"
    payload = {
        **result.as_dict(),
        "target_s": 10.0,
        "within_slo": result.elapsed_s <= 10.0,
        "note": "synthetic 10y-minute scale (250d×240min×10); not live ticks",
    }
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Soft gate: vectorized synthetic 10y must finish in 10s on CI hardware.
    assert result.elapsed_s <= 10.0, f"10y minute vectorized {result.elapsed_s:.3f}s > 10s"
