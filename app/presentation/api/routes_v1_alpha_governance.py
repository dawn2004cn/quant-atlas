"""API v1: Federated alpha governance (proposals, votes, audit history)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import current_user, login_required

from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.core.mesh.alpha_governance import ZeroKnowledgePerformanceProof, get_alpha_governance
from app.core.registry import register_routes
from app.infrastructure.mlflow.registry import ModelRegistry
from app.presentation.api.common import ok_response
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def _voter_team() -> str:
    user = getattr(current_user, "username", None) or getattr(current_user, "id", None)
    return str(user or "anonymous")


@register_routes(name="alpha_governance", context="system", description="Alpha factor governance DAO")
def register_alpha_governance_routes(bp: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @bp.get("/alpha/governance/stats")
    @login_required
    def alpha_governance_stats():
        dao = get_alpha_governance()
        return ok_response(
            data={
                "stats": dao.stats(),
                "active_factors": dao.get_active_factors(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/alpha/governance/proposals")
    @login_required
    def alpha_governance_proposals():
        dao = get_alpha_governance()
        return ok_response(
            data={"proposals": dao.list_proposals()},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/alpha/governance/proposals/<proposal_id>")
    @login_required
    def alpha_governance_proposal_detail(proposal_id: str):
        dao = get_alpha_governance()
        detail = dao.get_proposal(proposal_id)
        if detail is None:
            raise ValidationError("proposal not found")
        return ok_response(
            data={"proposal": detail},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/alpha/governance/votes")
    @login_required
    def alpha_governance_votes():
        proposal_id = (request.args.get("proposal_id") or "").strip() or None
        dao = get_alpha_governance()
        return ok_response(
            data={"votes": dao.list_vote_history(proposal_id)},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.get("/alpha/governance/workbench")
    @login_required
    def alpha_governance_workbench():
        """Aggregate governance, MLflow runs, and mined factors for UI workbench."""
        limit = request.args.get("limit", 10, type=int)
        limit = max(1, min(limit, 50))
        dao = get_alpha_governance()
        mining_factors: list[dict[str, object]] = []
        try:
            from app.modules.strategy.services.alpha_mining_service import AutoAlphaMiningService

            mining_factors = AutoAlphaMiningService().list_discovered_factors(sort_by="sharpe")[:limit]
        except Exception as exc:
            logger.warning("alpha_governance workbench mining factors: %s", exc, exc_info=True)
        return ok_response(
            data={
                "stats": dao.stats(),
                "active_factors": dao.get_active_factors(),
                "proposals": dao.list_proposals(),
                "votes": dao.list_vote_history(),
                "mlflow": {
                    "available": ModelRegistry.is_available(),
                    "config": ModelRegistry.get_tracking_config(),
                    "runs": ModelRegistry.list_recent_runs(max_results=limit),
                },
                "mining_factors": mining_factors,
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.post("/alpha/governance/proposals")
    @login_required
    def alpha_governance_submit_proposal():
        payload = request.get_json(silent=True) or {}
        strategy_id = (payload.get("strategy_id") or "").strip()
        expression = (payload.get("expression") or "").strip()
        if not strategy_id:
            raise ValidationError("strategy_id is required")
        if not expression:
            raise ValidationError("expression is required")
        metrics = payload.get("performance_metrics") or payload.get("metrics") or {}
        if not isinstance(metrics, dict):
            raise ValidationError("performance_metrics must be an object")
        metrics_f = {str(k): float(v) for k, v in metrics.items()}
        manager_id = (payload.get("manager_id") or _voter_team()).strip()
        zk_proof = (payload.get("zk_proof") or "").strip()
        if not zk_proof:
            zk_proof = ZeroKnowledgePerformanceProof.generate_proof(metrics_f)
        dao = get_alpha_governance()
        proposal_id = dao.submit_proposal(
            strategy_id=strategy_id,
            manager_id=manager_id,
            expression=expression,
            zk_proof=zk_proof,
            metrics=metrics_f,
            mlflow_run_id=(payload.get("mlflow_run_id") or "").strip() or None,
            mining_factor_id=(payload.get("mining_factor_id") or "").strip() or None,
        )
        return ok_response(
            data={"proposal_id": proposal_id, "proposal": dao.get_proposal(proposal_id)},
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )

    @bp.post("/alpha/governance/vote")
    @login_required
    def alpha_governance_vote():
        payload = request.get_json(silent=True) or {}
        proposal_id = (payload.get("proposal_id") or "").strip()
        if not proposal_id:
            raise ValidationError("proposal_id is required")
        approve = bool(payload.get("approve"))
        rationale = (payload.get("rationale") or "").strip()
        voter_team = (payload.get("voter_team") or _voter_team()).strip()
        dao = get_alpha_governance()
        if not dao.vote(proposal_id, voter_team, approve=approve, rationale=rationale):
            raise ValidationError("proposal not found or vote rejected")
        tally = dao.tally_votes(proposal_id)
        return ok_response(
            data={
                "proposal_id": proposal_id,
                "tally": tally,
                "vote_history": dao.list_vote_history(proposal_id),
            },
            legacy_alias_key=None,
            enable_legacy_alias=False,
        )
