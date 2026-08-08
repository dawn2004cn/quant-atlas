"""Feature pipeline predict / score tests."""

from __future__ import annotations

from app.domain.alpha.feature_pipeline import FeatureSpec, run_feature_pipeline
from app.domain.alpha.feature_pipeline_predict import predict_symbol
from app.modules.data.services.feature_pipeline_bars import synthetic_day_bars


def test_predict_heuristic_after_train(tmp_path):
    bars = synthetic_day_bars(periods=120)
    trained = run_feature_pipeline(
        bars,
        spec=FeatureSpec(name="cn_day_v0"),
        out_dir=tmp_path,
        train=True,
        model_backend="heuristic",
    )
    assert trained.model_path
    out = predict_symbol(
        symbol="SYN",
        spec_name="cn_day_v0",
        models_dir=tmp_path,
        bars=bars,
        prefer_live_bars=False,
    )
    assert out["ok"] is True
    assert out["model_type"] in {"ridge_heuristic", "corr_heuristic"}
    assert isinstance(out["latest_score"], float)
    assert out["n_scored"] >= 1
    assert out["tail"]


def test_predict_without_registry(tmp_path):
    out = predict_symbol(
        models_dir=tmp_path / "empty",
        bars=synthetic_day_bars(periods=80),
        prefer_live_bars=False,
    )
    assert out["ok"] is False
    assert "feature_model_not_found" in str(out.get("error"))
