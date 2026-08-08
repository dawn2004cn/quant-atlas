"""Score latest bars with Feature Pipeline registry (heuristic weights or LightGBM)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.logger import get_logger
from app.domain.alpha.feature_pipeline import FeatureSpec, _ensure_datetime

logger = get_logger(__name__)


def default_models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "instance" / "feature_models"


def load_registry(
    *,
    spec_name: str = "cn_day_v0",
    models_dir: Path | str | None = None,
) -> dict[str, Any]:
    root = Path(models_dir) if models_dir else default_models_dir()
    path = root / f"{spec_name}_latest.json"
    if not path.exists():
        raise FileNotFoundError(f"feature_model_not_found:{path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("feature_model_invalid")
    data["_registry_path"] = str(path)
    return data


def _spec_from_registry(registry: dict[str, Any]) -> FeatureSpec:
    raw = registry.get("spec") or {}
    if not isinstance(raw, dict):
        return FeatureSpec()
    cols = raw.get("columns") or FeatureSpec().columns
    if isinstance(cols, list):
        cols = tuple(str(c) for c in cols)
    return FeatureSpec(
        name=str(raw.get("name") or "cn_day_v0"),
        columns=tuple(cols),  # type: ignore[arg-type]
        lookback=int(raw.get("lookback") or 20),
        normalize=str(raw.get("normalize") or "zscore"),
        label_horizon=int(raw.get("label_horizon") or 5),
        price_col=str(raw.get("price_col") or "close"),
        date_col=str(raw.get("date_col") or "date"),
    )


def build_feature_frame_for_infer(df: pd.DataFrame, spec: FeatureSpec | None = None) -> pd.DataFrame:
    """Feature rows for inference: no forward-label requirement (keeps latest bar)."""
    spec = spec or FeatureSpec()
    if df is None or df.empty:
        return pd.DataFrame()
    frame = _ensure_datetime(df, spec.date_col)
    if spec.price_col not in frame.columns:
        return pd.DataFrame()
    close = frame[spec.price_col].astype(float)
    out = pd.DataFrame(index=frame.index)
    if spec.date_col in frame.columns:
        out[spec.date_col] = frame[spec.date_col]
    out["ret_1"] = close.pct_change(1)
    out["ret_5"] = close.pct_change(5)
    ma5 = close.rolling(5, min_periods=5).mean()
    ma20 = close.rolling(20, min_periods=20).mean()
    out["ma_bias_5"] = close / ma5 - 1.0
    out["ma_bias_20"] = close / ma20 - 1.0
    vol = close.pct_change().rolling(20, min_periods=20).std()
    out["vol_z_20"] = (close.pct_change() - close.pct_change().rolling(20).mean()) / vol.replace(0, pd.NA)
    cols = [c for c in spec.columns if c in out.columns]
    keep = ([spec.date_col] if spec.date_col in out.columns else []) + cols
    out = out[keep].dropna().reset_index(drop=True)
    if spec.normalize == "zscore" and cols and not out.empty:
        for col in cols:
            mu = out[col].mean()
            sigma = out[col].std()
            if sigma and float(sigma) > 0:
                out[col] = (out[col] - mu) / sigma
    elif spec.normalize == "minmax" and cols and not out.empty:
        for col in cols:
            lo = out[col].min()
            hi = out[col].max()
            if hi > lo:
                out[col] = (out[col] - lo) / (hi - lo)
    return out


def _score_heuristic_row(row: pd.Series, weights: dict[str, float], cols: list[str]) -> float:
    score = 0.0
    for c in cols:
        w = float(weights.get(c) or 0.0)
        try:
            score += w * float(row[c])
        except (TypeError, ValueError, KeyError):
            continue
    return float(score)


def _score_lightgbm_frame(frame: pd.DataFrame, cols: list[str], artifact_path: str) -> list[float]:
    import lightgbm as lgb

    booster = lgb.Booster(model_file=artifact_path)
    x = frame[cols].astype(float)
    preds = booster.predict(x)
    return [float(p) for p in preds]


def score_feature_frame(
    feature_df: pd.DataFrame,
    registry: dict[str, Any],
) -> dict[str, Any]:
    """Score all rows; returns latest score + series tail."""
    if feature_df is None or feature_df.empty:
        return {"ok": False, "error": "empty_features"}
    model = registry.get("model") or {}
    if not isinstance(model, dict) or not model.get("ok"):
        return {"ok": False, "error": "registry_model_not_ok"}
    spec = _spec_from_registry(registry)
    cols = [c for c in spec.columns if c in feature_df.columns]
    if not cols:
        return {"ok": False, "error": "no_feature_columns"}

    model_type = str(model.get("model_type") or "")
    if model_type == "lightgbm":
        artifact = model.get("artifact_path")
        if not artifact or not Path(str(artifact)).exists():
            return {"ok": False, "error": "lightgbm_artifact_missing", "model_type": model_type}
        try:
            scores = _score_lightgbm_frame(feature_df, cols, str(artifact))
        except Exception as exc:
            logger.warning("lightgbm predict failed: %s", exc, exc_info=True)
            return {"ok": False, "error": f"lightgbm_predict_failed:{exc}", "model_type": model_type}
    else:
        weights = model.get("weights") or {}
        if not isinstance(weights, dict) or not weights:
            return {"ok": False, "error": "heuristic_weights_missing", "model_type": model_type}
        scores = [_score_heuristic_row(feature_df.iloc[i], weights, cols) for i in range(len(feature_df))]

    date_col = spec.date_col if spec.date_col in feature_df.columns else None
    latest_idx = len(scores) - 1
    latest_date = str(feature_df.iloc[latest_idx][date_col]) if date_col is not None else None
    tail_n = min(10, len(scores))
    tail: list[dict[str, Any]] = []
    for i in range(len(scores) - tail_n, len(scores)):
        item: dict[str, Any] = {"score": round(scores[i], 8)}
        if date_col is not None:
            item["date"] = str(feature_df.iloc[i][date_col])
        tail.append(item)

    return {
        "ok": True,
        "model_type": model_type,
        "n_scored": len(scores),
        "latest_score": round(scores[latest_idx], 8),
        "latest_date": latest_date,
        "tail": tail,
        "feature_columns": cols,
        "registry_path": registry.get("_registry_path"),
        "trained_at": registry.get("trained_at"),
        "valid_ic": model.get("valid_ic"),
    }


def predict_symbol(
    *,
    symbol: str | None = None,
    spec_name: str = "cn_day_v0",
    models_dir: Path | str | None = None,
    bars: list[dict[str, Any]] | None = None,
    prefer_live_bars: bool = True,
) -> dict[str, Any]:
    """Load latest registry, build features from bars, return latest score."""
    from app.modules.data.services.feature_pipeline_bars import (
        load_cn_day_bars,
        synthetic_day_bars,
    )

    try:
        registry = load_registry(spec_name=spec_name, models_dir=models_dir)
    except FileNotFoundError as exc:
        return {"ok": False, "error": str(exc), "hint": "POST /data/feature-pipeline/train first"}
    except Exception as exc:
        return {"ok": False, "error": f"registry_load_failed:{exc}"}

    bar_meta: dict[str, Any] = {"synthetic": False}
    resolved_bars = bars
    if resolved_bars is None and prefer_live_bars:
        loaded = load_cn_day_bars(symbol=symbol)
        if loaded.get("ok") and loaded.get("bars"):
            resolved_bars = list(loaded["bars"])
            bar_meta = {
                "synthetic": False,
                "source": loaded.get("source"),
                "symbol": loaded.get("symbol"),
                "n_bars": loaded.get("n_bars"),
            }
        else:
            bar_meta["live_error"] = loaded.get("error")
    if not resolved_bars:
        resolved_bars = synthetic_day_bars(periods=160)
        bar_meta = {
            "synthetic": True,
            "source": "synthetic",
            "live_error": bar_meta.get("live_error"),
        }

    spec = _spec_from_registry(registry)
    frame = build_feature_frame_for_infer(pd.DataFrame(resolved_bars), spec)
    if frame.empty:
        return {"ok": False, "error": "empty_features_after_build", "bar_meta": bar_meta}

    scored = score_feature_frame(frame, registry)
    scored["symbol"] = bar_meta.get("symbol") or symbol
    scored["bar_meta"] = bar_meta
    scored["spec_name"] = spec.name
    return scored
