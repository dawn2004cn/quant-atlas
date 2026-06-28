"""MLflow model registry — optional; no-ops when mlflow is not installed."""

from __future__ import annotations

import re
from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime

logger = get_logger(__name__)


def _should_register_models() -> bool:
    return get_runtime("MLFLOW_REGISTER_MODELS", "0").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _sanitize_model_name(name: str) -> str:
    safe = re.sub(r"[^\w\-.]", "_", (name or "").strip())[:128]
    return safe or "quant_atlas_backtest"


class ModelRegistry:
    """Log backtest runs to MLflow when the optional dependency is available."""

    @staticmethod
    def is_available() -> bool:
        try:
            import mlflow

            return True
        except ImportError:
            return False

    @staticmethod
    def get_tracking_config() -> dict[str, Any]:
        """Public MLflow configuration for UI deep links."""
        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        return {
            "available": ModelRegistry.is_available(),
            "tracking_uri": tracking_uri or None,
            "experiment": get_runtime("MLFLOW_EXPERIMENT", "quant-atlas-backtest"),
            "register_models": _should_register_models(),
        }

    @staticmethod
    def build_run_ui_url(run_id: str, experiment_id: str | None = None) -> str | None:
        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        rid = (run_id or "").strip()
        if not tracking_uri or not rid:
            return None
        base = tracking_uri.rstrip("/")
        exp = experiment_id or "0"
        return f"{base}/#/experiments/{exp}/runs/{rid}"

    @staticmethod
    def log_backtest(
        name: str,
        *,
        symbol: str,
        strategy_name: str,
        metrics: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Record a backtest run. Returns run metadata, or None if skipped."""
        if not ModelRegistry.is_available():
            logger.debug("mlflow not installed; skip backtest log for %s", name)
            return None

        import mlflow

        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        experiment = get_runtime("MLFLOW_EXPERIMENT", "quant-atlas-backtest")
        mlflow.set_experiment(experiment)

        run_params = {
            "symbol": symbol,
            "strategy_name": strategy_name,
            **(params or {}),
        }
        numeric_metrics = {
            k: float(v)
            for k, v in metrics.items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }

        try:
            with mlflow.start_run(run_name=name) as run:
                mlflow.log_params({k: str(v) for k, v in run_params.items()})
                for key, value in numeric_metrics.items():
                    mlflow.log_metric(key, value)
                mlflow.log_dict(
                    {**numeric_metrics, "symbol": symbol, "strategy_name": strategy_name},
                    "backtest_summary.json",
                )
                payload: dict[str, Any] = {
                    "run_id": run.info.run_id,
                    "experiment_id": run.info.experiment_id,
                    "ui_url": ModelRegistry.build_run_ui_url(
                        run.info.run_id,
                        run.info.experiment_id,
                    ),
                }
                if _should_register_models():
                    registered = ModelRegistry._register_backtest_model(
                        run.info.run_id,
                        name,
                        numeric_metrics,
                    )
                    if registered:
                        payload.update(registered)
                return payload
        except Exception:
            logger.warning("MLflow backtest log failed", exc_info=True)
            return None

    @staticmethod
    def _register_backtest_model(
        run_id: str,
        model_name: str,
        metrics: dict[str, Any],
    ) -> dict[str, str] | None:
        """Register a lightweight pyfunc model snapshot for the backtest run."""
        try:
            import mlflow
            import mlflow.pyfunc

            class _BacktestSummaryPyfunc(mlflow.pyfunc.PythonModel):
                def predict(self, context, model_input):
                    import pandas as pd

                    return pd.DataFrame([{"status": "backtest_summary"}])

            safe_name = _sanitize_model_name(model_name)
            with mlflow.start_run(run_id=run_id):
                mlflow.log_dict(metrics, "model_metrics.json")
                model_info = mlflow.pyfunc.log_model(
                    artifact_path="backtest_model",
                    python_model=_BacktestSummaryPyfunc(),
                    registered_model_name=safe_name,
                )
            version = getattr(model_info, "registered_model_version", None)
            return {
                "model_name": safe_name,
                "model_version": str(version) if version is not None else "",
            }
        except Exception:
            logger.warning("MLflow model registration skipped", exc_info=True)
            return None

    @staticmethod
    def list_recent_runs(max_results: int = 20) -> list[dict[str, Any]]:
        """Return recent experiment runs, or [] when MLflow is unavailable."""
        if not ModelRegistry.is_available():
            return []

        import mlflow
        from mlflow.tracking import MlflowClient

        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        experiment = get_runtime("MLFLOW_EXPERIMENT", "quant-atlas-backtest")
        client = MlflowClient()
        exp = client.get_experiment_by_name(experiment)
        if exp is None:
            return []

        try:
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=max(1, min(max_results, 100)),
                order_by=["start_time DESC"],
            )
        except Exception:
            logger.warning("MLflow list runs failed", exc_info=True)
            return []

        items: list[dict[str, Any]] = []
        for run in runs:
            items.append(
                {
                    "run_id": run.info.run_id,
                    "run_name": run.info.run_name or run.info.run_id[:8],
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "experiment_id": run.info.experiment_id,
                    "ui_url": ModelRegistry.build_run_ui_url(
                        run.info.run_id,
                        run.info.experiment_id,
                    ),
                    "metrics": dict(run.data.metrics),
                    "params": dict(run.data.params),
                }
            )
        return items

    @staticmethod
    def get_run(run_id: str) -> dict[str, Any] | None:
        """Return a single MLflow run by id, or None when unavailable / not found."""
        rid = (run_id or "").strip()
        if not rid or not ModelRegistry.is_available():
            return None

        import mlflow
        from mlflow.exceptions import MlflowException
        from mlflow.tracking import MlflowClient

        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        try:
            run = MlflowClient().get_run(rid)
        except MlflowException:
            return None
        except Exception:
            logger.warning("MLflow get_run failed for %s", rid, exc_info=True)
            return None

        return {
            "run_id": run.info.run_id,
            "run_name": run.info.run_name or run.info.run_id[:8],
            "status": run.info.status,
            "start_time": run.info.start_time,
            "end_time": run.info.end_time,
            "experiment_id": run.info.experiment_id,
            "ui_url": ModelRegistry.build_run_ui_url(
                run.info.run_id,
                run.info.experiment_id,
            ),
            "metrics": dict(run.data.metrics),
            "params": dict(run.data.params),
        }

    @staticmethod
    def list_registered_models(max_results: int = 20) -> list[dict[str, Any]]:
        """Return registered model versions with optional linked run metrics."""
        if not ModelRegistry.is_available():
            return []

        import mlflow
        from mlflow.tracking import MlflowClient

        tracking_uri = get_runtime("MLFLOW_TRACKING_URI", "").strip()
        if tracking_uri:
            mlflow.set_tracking_uri(tracking_uri)

        client = MlflowClient()
        try:
            versions = client.search_model_versions(
                max_results=max(1, min(max_results, 100)),
                order_by=["version_number DESC"],
            )
        except Exception:
            logger.warning("MLflow list registered models failed", exc_info=True)
            return []

        items: list[dict[str, Any]] = []
        for model_version in versions:
            row: dict[str, Any] = {
                "name": model_version.name,
                "version": model_version.version,
                "stage": model_version.current_stage,
                "run_id": model_version.run_id,
                "status": model_version.status,
            }
            if model_version.run_id:
                run = ModelRegistry.get_run(model_version.run_id)
                if run:
                    row["metrics"] = run.get("metrics", {})
                    row["params"] = run.get("params", {})
            items.append(row)
        return items
