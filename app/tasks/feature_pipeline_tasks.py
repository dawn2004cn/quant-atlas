"""Celery / sync entry for Feature Pipeline training (heuristic or LightGBM)."""

from __future__ import annotations

from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime
from app.domain.alpha.feature_pipeline import FeatureSpec, run_feature_pipeline

logger = get_logger(__name__)


def run_feature_pipeline_tick(
    *,
    bars: list[dict[str, Any]] | None = None,
    spec_name: str = "cn_day_v0",
    model_backend: str | None = None,
    symbol: str | None = None,
    prefer_live_bars: bool = True,
) -> dict[str, Any]:
    """Run feature build + train (``FEATURE_PIPELINE_MODEL``: auto|lightgbm|heuristic).

    Bar resolution order:
    1. Explicit ``bars`` argument
    2. Live CN dayK via multi-source history (``FEATURE_PIPELINE_SYMBOL``) when ``prefer_live_bars``
    3. Synthetic series (CI / empty-data fallback; does not claim live alpha)
    """
    from app.modules.data.services.feature_pipeline_bars import (
        load_cn_day_bars,
        synthetic_day_bars,
    )

    backend = (model_backend or get_runtime("FEATURE_PIPELINE_MODEL", "auto") or "auto").strip()
    bar_meta: dict[str, Any] = {"synthetic": True, "source": "synthetic"}
    if bars is None and prefer_live_bars:
        loaded = load_cn_day_bars(symbol=symbol)
        if loaded.get("ok") and loaded.get("bars"):
            bars = list(loaded["bars"])
            bar_meta = {
                "synthetic": False,
                "source": loaded.get("source"),
                "symbol": loaded.get("symbol"),
                "n_bars_raw": loaded.get("n_bars"),
                "range": {"start": loaded.get("start"), "end": loaded.get("end")},
            }
        else:
            bar_meta["live_error"] = loaded.get("error")
            logger.info(
                "feature_pipeline live bars unavailable (%s); using synthetic",
                loaded.get("error"),
            )

    if not bars:
        bars = synthetic_day_bars(periods=160)
        bar_meta = {"synthetic": True, "source": "synthetic", "live_error": bar_meta.get("live_error")}

    result = run_feature_pipeline(
        bars,
        spec=FeatureSpec(name=spec_name),
        train=True,
        model_backend=backend,
    )
    payload = {
        "ok": result.n_rows > 0,
        "spec_name": result.spec_name,
        "n_rows": result.n_rows,
        "feature_columns": result.feature_columns,
        "model_path": result.model_path,
        "registry_path": result.registry_path,
        "notes": result.notes,
        "model_backend": backend,
        "synthetic_bars": bool(bar_meta.get("synthetic")),
        "bars_source": bar_meta.get("source"),
        "symbol": bar_meta.get("symbol") or symbol or get_runtime("FEATURE_PIPELINE_SYMBOL", ""),
        "bar_meta": bar_meta,
    }
    logger.info(
        "feature_pipeline_tick n_rows=%s backend=%s synthetic=%s source=%s model=%s",
        result.n_rows,
        backend,
        payload["synthetic_bars"],
        payload["bars_source"],
        result.model_path,
    )
    return payload


try:
    from app.celery_app import celery
except Exception:  # pragma: no cover
    celery = None  # type: ignore

if celery is not None:

    @celery.task(name="app.tasks.feature_pipeline_tasks.feature_pipeline_tick")
    def feature_pipeline_tick(
        spec_name: str = "cn_day_v0",
        model_backend: str | None = None,
        symbol: str | None = None,
    ) -> dict[str, Any]:
        return run_feature_pipeline_tick(
            spec_name=spec_name,
            model_backend=model_backend,
            symbol=symbol,
        )
