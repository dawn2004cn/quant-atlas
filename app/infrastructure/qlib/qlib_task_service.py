from __future__ import annotations
"""Qlib task service stub implementation - placeholder for rd-agent to qlib pipeline.

This is a stub implementation for development/testing.
A full implementation would integrate with qlib's execution engine.
"""


import uuid
from datetime import datetime
from typing import Any

from ...core.logger import get_logger
from ...domain.ports.qlib_task_ports import QlibExperimentResult, QlibTaskService

logger = get_logger(__name__)


class QlibTaskServiceStub(QlibTaskService):
    """Stub implementation of QlibTaskService for development.

    This creates in-memory experiment records that can be used
    for testing the rd-agent -> qlib pipeline integration.
    """

    def __init__(self) -> None:
        self._experiments: dict[str, dict[str, Any]] = {}

    def submit_experiment(
        self,
        formula: str,
        *,
        data_scope: dict[str, Any] | None = None,
        model_config: dict[str, Any] | None = None,
        backtest_config: dict[str, Any] | None = None,
    ) -> str:
        exp_id = f"exp_{uuid.uuid4().hex[:12]}"
        self._experiments[exp_id] = {
            "experiment_id": exp_id,
            "formula": formula,
            "status": "pending",
            "data_scope": data_scope or {},
            "model_config": model_config or {},
            "backtest_config": backtest_config or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        logger.info(f"Created experiment {exp_id}: {formula[:100]}")
        return exp_id

    def submit_formula_set(
        self,
        formulas: list[str],
        *,
        data_scope: dict[str, Any] | None = None,
    ) -> list[str]:
        exp_ids = []
        for formula in formulas:
            exp_id = self.submit_experiment(formula, data_scope=data_scope)
            exp_ids.append(exp_id)
        return exp_ids

    def get_experiment_result(self, experiment_id: str) -> QlibExperimentResult:
        exp = self._experiments.get(experiment_id)
        if not exp:
            return QlibExperimentResult(
                experiment_id=experiment_id,
                status="not_found",
                formula="",
                error="Experiment not found",
            )
        return QlibExperimentResult(
            experiment_id=exp["experiment_id"],
            status=exp["status"],
            formula=exp["formula"],
            backtest_result=exp.get("backtest_result"),
            model_result=exp.get("model_result"),
            error=exp.get("error"),
        )

    def update_experiment(
        self,
        experiment_id: str,
        status: str,
        backtest_result: dict[str, Any] | None = None,
        model_result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> bool:
        if experiment_id not in self._experiments:
            return False
        self._experiments[experiment_id]["status"] = status
        if backtest_result:
            self._experiments[experiment_id]["backtest_result"] = backtest_result
        if model_result:
            self._experiments[experiment_id]["model_result"] = model_result
        if error:
            self._experiments[experiment_id]["error"] = error
        return True

    def cancel_experiment(self, experiment_id: str) -> bool:
        if experiment_id in self._experiments:
            self._experiments[experiment_id]["status"] = "cancelled"
            return True
        return False

    def list_experiments(
        self,
        *,
        limit: int = 50,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        exps = list(self._experiments.values())
        if status:
            exps = [e for e in exps if e["status"] == status]
        exps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return exps[:limit]


def create_qlib_task_service() -> QlibTaskService:
    """Factory function to create QlibTaskService."""
    return QlibTaskServiceStub()