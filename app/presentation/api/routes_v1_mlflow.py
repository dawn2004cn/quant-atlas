"""API v1: MLflow experiment runs (optional dependency)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.mesh.alpha_governance import get_alpha_governance
from app.core.registry import register_routes
from app.infrastructure.mlflow.registry import ModelRegistry
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context


def _linked_proposals(run_id: str | None) -> list[dict[str, object]]:
    rid = (run_id or "").strip()
    if not rid:
        return []
    return get_alpha_governance().find_proposals_by_mlflow_run(rid)


@register_routes(name="mlflow", context="system", description="MLflow backtest run history")
def register_mlflow_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @bp.get("/mlflow/runs")
    @login_required
    def mlflow_recent_runs():
        limit = request.args.get("limit", 20, type=int)
        runs = ModelRegistry.list_recent_runs(max_results=limit)
        return ok_response(
            data={
                "runs": runs,
                "available": ModelRegistry.is_available(),
                "count": len(runs),
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/mlflow/runs/<run_id>")
    @login_required
    def mlflow_run_detail(run_id: str):
        detail = ModelRegistry.get_run(run_id)
        if detail is None:
            raise ValidationError("mlflow run not found")
        linked = _linked_proposals(run_id)
        return ok_response(
            data={
                "run": detail,
                "available": ModelRegistry.is_available(),
                "linked_proposals": linked,
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/mlflow/models")
    @login_required
    def mlflow_registered_models():
        limit = request.args.get("limit", 20, type=int)
        models = ModelRegistry.list_registered_models(max_results=limit)
        for row in models:
            row["linked_proposals"] = _linked_proposals(str(row.get("run_id") or ""))
        return ok_response(
            data={
                "models": models,
                "available": ModelRegistry.is_available(),
                "count": len(models),
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/mlflow/status")
    @login_required
    def mlflow_status():
        return ok_response(
            data=ModelRegistry.get_tracking_config(),
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )
