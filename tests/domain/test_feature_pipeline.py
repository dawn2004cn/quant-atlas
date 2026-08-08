"""Feature pipeline + LightGBM/heuristic trainer tests."""

from __future__ import annotations

import pandas as pd
import pytest

from app.domain.alpha.feature_pipeline import (
    FeatureSpec,
    build_feature_frame,
    run_feature_pipeline,
    train_lightgbm_model,
    train_model,
)
from app.tasks.feature_pipeline_tasks import run_feature_pipeline_tick


def _synth_bars(n: int = 120) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="B")
    close = [100 + (i % 10) * 0.4 + i * 0.05 for i in range(n)]
    return pd.DataFrame({"date": dates, "close": close})


def test_build_feature_frame_no_lookahead_in_features():
    out = build_feature_frame(_synth_bars(60), FeatureSpec(lookback=20, label_horizon=5))
    assert not out.empty
    assert "label_fwd" in out.columns
    assert "ret_1" in out.columns
    assert len(out) < 60


def test_run_feature_pipeline_heuristic(tmp_path):
    result = run_feature_pipeline(_synth_bars(80), out_dir=tmp_path, train=True, model_backend="heuristic")
    assert result.n_rows > 0
    assert result.model_path
    assert (tmp_path / "cn_day_v0_latest.json").exists()
    assert any("heuristic" in n for n in result.notes)


def test_train_model_auto_fallback_or_lgbm(tmp_path):
    feats = build_feature_frame(_synth_bars(100), FeatureSpec())
    out = train_model(
        feats,
        feature_columns=FeatureSpec().columns,
        backend="auto",
        model_dir=tmp_path,
        model_stem="t1",
    )
    assert out.get("ok") is True
    assert out.get("model_type") in {"lightgbm", "ridge_heuristic", "corr_heuristic"}


def test_train_lightgbm_explicit():
    feats = build_feature_frame(_synth_bars(100), FeatureSpec())
    out = train_lightgbm_model(feats, feature_columns=FeatureSpec().columns)
    if out.get("error") == "lightgbm_not_installed":
        pytest.skip("lightgbm not installed")
    assert out["ok"] is True
    assert out["model_type"] == "lightgbm"
    assert "valid_ic" in out
    assert out["valid_rows"] >= 5


def test_feature_pipeline_tick_synthetic():
    out = run_feature_pipeline_tick(model_backend="heuristic", prefer_live_bars=False)
    assert out["ok"] is True
    assert out["synthetic_bars"] is True
    assert out["model_backend"] == "heuristic"
