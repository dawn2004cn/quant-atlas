"""Feature Pipeline v0 — FreqAI-style FeatureSpec on local OHLCV (qlib-friendly).

Look-ahead safety: labels use forward returns shifted so feature row t only
sees prices up to t; training callers must still use time-based splits.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """Declarative feature recipe (day-bar defaults for A-shares)."""

    name: str = "cn_day_v0"
    columns: tuple[str, ...] = ("ret_1", "ret_5", "ma_bias_5", "ma_bias_20", "vol_z_20")
    lookback: int = 20
    normalize: str = "zscore"  # zscore | minmax | none
    label_horizon: int = 5
    price_col: str = "close"
    date_col: str = "date"


@dataclass
class FeaturePipelineResult:
    spec_name: str
    n_rows: int
    feature_columns: list[str]
    label_column: str
    model_path: str | None
    registry_path: str | None
    notes: list[str] = field(default_factory=list)


def _ensure_datetime(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = df.copy()
    if date_col in out.columns:
        out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
        out = out.sort_values(date_col).reset_index(drop=True)
    return out


def build_feature_frame(df: pd.DataFrame, spec: FeatureSpec | None = None) -> pd.DataFrame:
    """Build features + forward label without peeking future prices into features."""
    spec = spec or FeatureSpec()
    if df is None or df.empty:
        return pd.DataFrame()
    frame = _ensure_datetime(df, spec.date_col)
    if spec.price_col not in frame.columns:
        raise ValueError(f"missing_price_col:{spec.price_col}")
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
    # Label: forward return over horizon (known only after t+h — dropna before train)
    out["label_fwd"] = close.shift(-spec.label_horizon) / close - 1.0
    cols = [c for c in spec.columns if c in out.columns]
    keep = ([spec.date_col] if spec.date_col in out.columns else []) + cols + ["label_fwd"]
    out = out[keep].dropna().reset_index(drop=True)
    if spec.normalize == "zscore" and cols:
        for col in cols:
            mu = out[col].mean()
            sigma = out[col].std()
            if sigma and float(sigma) > 0:
                out[col] = (out[col] - mu) / sigma
    elif spec.normalize == "minmax" and cols:
        for col in cols:
            lo = out[col].min()
            hi = out[col].max()
            if hi > lo:
                out[col] = (out[col] - lo) / (hi - lo)
    return out


def train_heuristic_model(
    feature_df: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    label_column: str = "label_fwd",
) -> dict[str, Any]:
    """Train a tiny linear heuristic (no LightGBM required) and return weights."""
    import numpy as np

    cols = [c for c in feature_columns if c in feature_df.columns]
    if not cols or label_column not in feature_df.columns or feature_df.empty:
        return {"ok": False, "error": "insufficient_feature_rows", "weights": {}}
    x = feature_df[cols].astype(float).to_numpy()
    y = feature_df[label_column].astype(float).to_numpy()
    try:
        xtx = x.T @ x + np.eye(len(cols)) * 1e-3
        weights = np.linalg.solve(xtx, x.T @ y)
        wmap = {c: float(weights[i]) for i, c in enumerate(cols)}
        return {"ok": True, "model_type": "ridge_heuristic", "weights": wmap, "n_rows": int(len(feature_df))}
    except Exception:
        corr = {
            c: float(pd.Series(x[:, i]).corr(pd.Series(y)) or 0.0)
            for i, c in enumerate(cols)
        }
        return {"ok": True, "model_type": "corr_heuristic", "weights": corr, "n_rows": int(len(feature_df))}


def _time_split_xy(
    feature_df: pd.DataFrame,
    cols: list[str],
    label_column: str,
    *,
    train_ratio: float = 0.8,
) -> tuple[Any, Any, Any, Any, int]:
    import numpy as np

    n = len(feature_df)
    split = max(1, min(n - 1, int(n * train_ratio)))
    x = feature_df[cols].astype(float).to_numpy()
    y = feature_df[label_column].astype(float).to_numpy()
    return x[:split], y[:split], x[split:], y[split:], split


def train_lightgbm_model(
    feature_df: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    label_column: str = "label_fwd",
    model_dir: Path | str | None = None,
    model_stem: str | None = None,
) -> dict[str, Any]:
    """Train LightGBM regressor with time-based split; fall back errors if package missing."""
    cols = [c for c in feature_columns if c in feature_df.columns]
    if not cols or label_column not in feature_df.columns or len(feature_df) < 40:
        return {"ok": False, "error": "insufficient_feature_rows", "model_type": "lightgbm"}

    try:
        import lightgbm as lgb
        import numpy as np
    except ImportError:
        return {
            "ok": False,
            "error": "lightgbm_not_installed",
            "model_type": "lightgbm",
            "hint": "pip install lightgbm  # or pip install 'quant-atlas[ml]'",
        }

    x_train, y_train, x_valid, y_valid, split = _time_split_xy(
        feature_df, cols, label_column, train_ratio=0.8
    )
    if len(x_valid) < 5:
        return {"ok": False, "error": "valid_split_too_small", "model_type": "lightgbm"}

    x_train_df = pd.DataFrame(x_train, columns=cols)
    x_valid_df = pd.DataFrame(x_valid, columns=cols)
    model = lgb.LGBMRegressor(
        n_estimators=80,
        learning_rate=0.05,
        max_depth=4,
        num_leaves=15,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        verbosity=-1,
    )
    model.fit(x_train_df, y_train)
    pred = model.predict(x_valid_df)
    # Rank IC ≈ Pearson on small samples; also RMSE
    ic = float(pd.Series(pred).corr(pd.Series(y_valid)) or 0.0)
    rmse = float(np.sqrt(np.mean((pred - y_valid) ** 2)))
    importance = {
        c: float(v) for c, v in zip(cols, model.feature_importances_.tolist(), strict=False)
    }

    artifact: str | None = None
    if model_dir is not None:
        root = Path(model_dir)
        root.mkdir(parents=True, exist_ok=True)
        stem = model_stem or "lgbm"
        txt_path = root / f"{stem}.txt"
        try:
            model.booster_.save_model(str(txt_path))
            artifact = str(txt_path)
        except Exception:
            logger.warning("lightgbm save_model failed", exc_info=True)

    return {
        "ok": True,
        "model_type": "lightgbm",
        "n_rows": int(len(feature_df)),
        "train_rows": int(split),
        "valid_rows": int(len(y_valid)),
        "valid_ic": round(ic, 6),
        "valid_rmse": round(rmse, 6),
        "feature_importance": importance,
        "artifact_path": artifact,
        "backend": "lightgbm",
    }


def train_model(
    feature_df: pd.DataFrame,
    *,
    feature_columns: Sequence[str],
    label_column: str = "label_fwd",
    backend: str = "auto",
    model_dir: Path | str | None = None,
    model_stem: str | None = None,
) -> dict[str, Any]:
    """Train with ``lightgbm`` when available (``auto``), else ridge heuristic.

    ``backend``: auto | lightgbm | heuristic
    """
    mode = (backend or "auto").strip().lower()
    if mode in {"auto", "lightgbm", "lgb", "lgbm"}:
        lgb_result = train_lightgbm_model(
            feature_df,
            feature_columns=feature_columns,
            label_column=label_column,
            model_dir=model_dir,
            model_stem=model_stem,
        )
        if lgb_result.get("ok"):
            return lgb_result
        if mode in {"lightgbm", "lgb", "lgbm"}:
            return lgb_result
        logger.info(
            "feature_pipeline lightgbm unavailable (%s); falling back to heuristic",
            lgb_result.get("error"),
        )
        fallback = train_heuristic_model(
            feature_df, feature_columns=feature_columns, label_column=label_column
        )
        fallback["fallback_from"] = lgb_result.get("error")
        return fallback
    return train_heuristic_model(
        feature_df, feature_columns=feature_columns, label_column=label_column
    )


def run_feature_pipeline(
    bars: pd.DataFrame | list[dict[str, Any]],
    *,
    spec: FeatureSpec | None = None,
    out_dir: Path | str | None = None,
    train: bool = True,
    model_backend: str = "auto",
) -> FeaturePipelineResult:
    """Build features, optionally train, write model registry under instance/."""
    spec = spec or FeatureSpec()
    df = bars if isinstance(bars, pd.DataFrame) else pd.DataFrame(bars)
    features = build_feature_frame(df, spec)
    notes: list[str] = []
    if features.empty:
        notes.append("empty_features_after_dropna")
        return FeaturePipelineResult(
            spec_name=spec.name,
            n_rows=0,
            feature_columns=list(spec.columns),
            label_column="label_fwd",
            model_path=None,
            registry_path=None,
            notes=notes,
        )

    root = Path(out_dir) if out_dir else Path(__file__).resolve().parents[3] / "instance" / "feature_models"
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_path: str | None = None
    registry_path: str | None = None
    model_payload: dict[str, Any] = {"ok": False}
    if train:
        model_payload = train_model(
            features,
            feature_columns=spec.columns,
            backend=model_backend,
            model_dir=root,
            model_stem=f"{spec.name}_{ts}",
        )
        model_file = root / f"{spec.name}_{ts}.json"
        registry = {
            "spec": asdict(spec),
            "trained_at": ts,
            "model_backend": model_backend,
            "model": model_payload,
            "n_rows": int(len(features)),
            "lookahead_note": "label_fwd uses shift(-horizon); features use only past/current prices; time-split train/valid",
        }
        model_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        latest = root / f"{spec.name}_latest.json"
        latest.write_text(model_file.read_text(encoding="utf-8"), encoding="utf-8")
        model_path = str(model_file)
        registry_path = str(latest)
        notes.append(str(model_payload.get("model_type") or "trained"))
        if model_payload.get("fallback_from"):
            notes.append(f"fallback_from:{model_payload['fallback_from']}")
        if model_payload.get("valid_ic") is not None:
            notes.append(f"valid_ic={model_payload['valid_ic']}")
    return FeaturePipelineResult(
        spec_name=spec.name,
        n_rows=int(len(features)),
        feature_columns=list(spec.columns),
        label_column="label_fwd",
        model_path=model_path,
        registry_path=registry_path,
        notes=notes,
    )
