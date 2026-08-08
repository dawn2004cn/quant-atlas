"""Feature pipeline bar loader + live-prefer tick tests."""

from __future__ import annotations

from app.modules.data.services.feature_pipeline_bars import _bar_to_row, synthetic_day_bars
from app.tasks.feature_pipeline_tasks import run_feature_pipeline_tick


def test_bar_to_row_normalizes_trade_date():
    row = _bar_to_row({"trade_date": "2024-01-02", "close": 10.5, "open": 10.0})
    assert row is not None
    assert row["date"] == "2024-01-02"
    assert row["close"] == 10.5


def test_synthetic_day_bars_enough_for_train():
    rows = synthetic_day_bars(periods=100)
    assert len(rows) >= 80
    assert "close" in rows[0]


def test_tick_uses_live_bars_when_loader_ok(monkeypatch, tmp_path):
    live = {
        "ok": True,
        "bars": synthetic_day_bars(periods=120),
        "symbol": "600519",
        "source": "timescale_mock",
        "n_bars": 120,
        "start": "2023-01-01",
        "end": "2023-06-01",
        "synthetic": False,
    }
    monkeypatch.setattr(
        "app.modules.data.services.feature_pipeline_bars.load_cn_day_bars",
        lambda **kwargs: live,
    )

    import app.domain.alpha.feature_pipeline as fp

    real_run = fp.run_feature_pipeline

    def _run(bars, **kwargs):
        kwargs["out_dir"] = tmp_path
        return real_run(bars, **kwargs)

    monkeypatch.setattr(
        "app.tasks.feature_pipeline_tasks.run_feature_pipeline",
        _run,
    )
    out = run_feature_pipeline_tick(model_backend="heuristic", prefer_live_bars=True)
    assert out["ok"] is True
    assert out["synthetic_bars"] is False
    assert out["bars_source"] == "timescale_mock"
    assert out["symbol"] == "600519"


def test_tick_falls_back_synthetic_when_live_fails(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "app.modules.data.services.feature_pipeline_bars.load_cn_day_bars",
        lambda **kwargs: {"ok": False, "bars": [], "error": "insufficient_bars:0<60", "synthetic": False},
    )
    import app.domain.alpha.feature_pipeline as fp

    real_run = fp.run_feature_pipeline

    def _run(bars, **kwargs):
        kwargs["out_dir"] = tmp_path
        return real_run(bars, **kwargs)

    monkeypatch.setattr("app.tasks.feature_pipeline_tasks.run_feature_pipeline", _run)
    out = run_feature_pipeline_tick(model_backend="heuristic", prefer_live_bars=True)
    assert out["ok"] is True
    assert out["synthetic_bars"] is True
    assert out["bar_meta"].get("live_error")
