from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Research Ops: Automated Forward Testing and Factor Monitoring."""


from typing import Any, Optional
import inspect
from datetime import datetime, timezone

from app.core.logger import get_logger
from app.domain.alpha.factor_manager import FactorDecayDetector, FactorMetrics
from app.domain.ports import IExperimentRepository

logger = get_logger(__name__)

_DECAY_RATE_THRESHOLD = 0.35


class ForwardTestingService:
    """Automated Forward Testing Service to validate signals before live deployment."""

    def __init__(
        self,
        swarm_runtime: object = None,
        experiment_repo: Optional[IExperimentRepository] = None,
    ):
        if swarm_runtime is not None:
            self._swarm_runtime = swarm_runtime
        else:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            from app.domain.ports.agent_ports import SwarmOrchestratorPort
            self._swarm_runtime = resolve_optional_service(SwarmOrchestratorPort)
        if self._swarm_runtime is None:
            from app.modules.system.services.helpers.agent_access import create_default_swarm_runtime
            self._swarm_runtime = create_default_swarm_runtime()
        self._experiment_repo = experiment_repo

    @property
    def experiment_repo(self):
        if self._experiment_repo is None:
            from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service
            self._experiment_repo = resolve_optional_service(IExperimentRepository)
        return self._experiment_repo

    def validate_signal(self, symbol: str, signal_data: dict[str, Any]) -> GenericResponseDTO:
        """Trigger a forward test swarm to validate a signal."""
        logger.info(f"Initiating forward testing for {symbol}")
        run = self._swarm_runtime.start_run(
            preset_name="validation_swarm",
            user_vars={"symbol": symbol, "signal": str(signal_data)}
        )
        return {"ok": True, "run_id": run.id}

class FactorDecayMonitor:
    """Monitors alpha factor performance and triggers retrain if decay detected."""

    def __init__(
        self,
        factor_repo: object,
        *,
        ir_threshold: float = 0.5,
        experiment_repo: Optional[Any] = None,
        swarm_runtime: object | None = None,
    ) -> None:
        self.factor_repo = factor_repo
        self._detector = FactorDecayDetector(ir_threshold=ir_threshold)
        self._experiment_repo = experiment_repo
        self._swarm_runtime = swarm_runtime

    def _resolve_experiment_repo(self) -> Any | None:
        if self._experiment_repo is not None:
            return self._experiment_repo
        from app.modules.system.services.helpers.service_resolver_access import resolve_optional_service

        repo = resolve_optional_service(IExperimentRepository)
        if repo is not None:
            return repo
        try:
            from app.modules.system.services.helpers.agent_access import create_default_experiment_repository

            return create_default_experiment_repository()
        except RuntimeError:
            return None

    def _resolve_swarm_runtime(self) -> Any | None:
        if self._swarm_runtime is not None:
            return self._swarm_runtime
        try:
            from app.modules.system.services.helpers.agent_access import create_default_swarm_runtime

            return create_default_swarm_runtime()
        except RuntimeError:
            return None

    def _fetch_factor_row(self, factor_id: str) -> dict[str, Any] | None:
        repo = self.factor_repo
        if repo is None:
            return None
        if hasattr(repo, "get_factor"):
            row = repo.get_factor(factor_id)
        elif hasattr(repo, "get_factor_metadata"):
            row = repo.get_factor_metadata(factor_id)
        else:
            row = None
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return {
            "factor_id": getattr(row, "factor_id", factor_id),
            "factor_name": getattr(row, "factor_name", factor_id),
            "ic_mean": float(getattr(row, "ic_mean", 0) or 0),
            "ic_std": float(getattr(row, "ic_std", 0) or 0),
            "ir": float(getattr(row, "ir", 0) or 0),
            "decay_rate": float(getattr(row, "decay_rate", 0) or 0),
        }

    def _metrics_from_row(self, factor_id: str, row: dict[str, Any]) -> FactorMetrics:
        name = str(row.get("factor_name") or row.get("factor_id") or factor_id)
        ic_mean = float(row.get("ic_mean") or 0)
        ic_std = float(row.get("ic_std") or 0) or 1.0
        ir = float(row.get("ir") or 0)
        return FactorMetrics(
            factor_name=name,
            ic_mean=ic_mean,
            ic_std=ic_std,
            ir=ir,
        )

    def _record_decay_event(self, factor_id: str, row: dict[str, Any], *, severity: str) -> None:
        repo = self.factor_repo
        if repo is None or not hasattr(repo, "log_decay_event"):
            return

        fn = repo.log_decay_event
        detection_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ic_current = float(row.get("ic_mean") or 0)
        ic_historical = float(row.get("ic_mean_historical") or ic_current)
        decay_ratio = float(row.get("decay_rate") or 0)

        if inspect.iscoroutinefunction(fn):
            payload = {
                "factor_id": factor_id,
                "detection_date": detection_date,
                "ic_mean_current": ic_current,
                "ic_mean_historical": ic_historical,
                "decay_ratio": decay_ratio,
                "severity": severity,
            }
            try:
                from app.tasks.factor_decay_tasks import log_factor_decay_event_task

                log_factor_decay_event_task.delay(payload)
            except Exception as exc:
                logger.debug("async log_decay_event enqueue skipped for %s: %s", factor_id, exc)
            return

        try:
            fn(
                factor_id=factor_id,
                detection_date=detection_date,
                ic_mean_current=ic_current,
                ic_mean_historical=ic_historical,
                decay_ratio=decay_ratio,
                severity=severity,
            )
        except TypeError:
            fn(factor_id, detection_date, ic_current, ic_historical, decay_ratio, severity)
        except Exception as exc:
            logger.warning("factor decay log failed for %s: %s", factor_id, exc)

    def check_decay(self, factor_id: str) -> bool:
        """Analyze factor precision decay via IR detector and decay_rate threshold."""
        row = self._fetch_factor_row(factor_id)
        if row is None:
            logger.info("factor metrics unavailable for %s", factor_id)
            return False

        metrics = self._metrics_from_row(factor_id, row)
        alert = self._detector.check_decay(metrics)
        if alert is not None:
            logger.info(
                "factor decay detected: %s severity=%s ir=%.4f",
                factor_id,
                alert.severity,
                alert.current_ir,
            )
            self._record_decay_event(factor_id, row, severity=alert.severity)
            return True

        decay_rate = float(row.get("decay_rate") or 0)
        if decay_rate >= _DECAY_RATE_THRESHOLD:
            logger.info(
                "factor decay_rate threshold exceeded: %s rate=%.4f",
                factor_id,
                decay_rate,
            )
            self._record_decay_event(factor_id, row, severity="warning")
            return True
        return False

    def trigger_retrain(self, factor_id: str) -> GenericResponseDTO:
        """Queue factor retrain experiment and optionally start swarm run."""
        logger.info("Triggering auto-retrain for factor: %s", factor_id)
        row = self._fetch_factor_row(factor_id) or {}
        experiment_payload = {
            "experiment_id": f"factor-retrain-{factor_id}",
            "name": f"Factor retrain {factor_id}",
            "factor_id": factor_id,
            "status": "queued",
            "trigger": "decay_monitor",
            "metadata": {
                "decay_rate": row.get("decay_rate"),
                "ir": row.get("ir"),
            },
        }

        experiment_result: Any = None
        repo = self._resolve_experiment_repo()
        if repo is not None:
            try:
                if hasattr(repo, "save_experiment"):
                    experiment_result = repo.save_experiment(experiment_payload)
                elif hasattr(repo, "update_experiment"):
                    experiment_result = repo.update_experiment(
                        str(experiment_payload["experiment_id"]),
                        experiment_payload,
                    )
            except Exception as exc:
                logger.warning("factor retrain experiment persist failed: %s", exc)

        run_id: str | None = None
        runtime = self._resolve_swarm_runtime()
        if runtime is not None and hasattr(runtime, "start_run"):
            try:
                run = runtime.start_run(
                    preset_name="factor_retrain",
                    user_vars={"factor_id": factor_id},
                )
                run_id = str(getattr(run, "id", "") or "")
            except Exception as exc:
                logger.warning("factor retrain swarm start failed: %s", exc)

        return {
            "ok": True,
            "factor_id": factor_id,
            "experiment": experiment_result,
            "run_id": run_id,
        }


__all__ = ["ForwardTestingService", "FactorDecayMonitor"]
