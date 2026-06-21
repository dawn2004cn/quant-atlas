"""Human-in-the-loop decision review queue routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.trade_plan.runtime import TradePlanRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_decision_review_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: TradePlanRuntime,
) -> None:
    _ = ctx
    legacy = runtime.ctx.enable_legacy_response_fields

    @blueprint.get("/decision/review-queue")
    @login_required
    def decision_review_queue():
        """List pending decisions needing human review."""
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        q = get_review_queue()
        limit = int(request.args.get("limit", 50))
        items = q.list_pending(limit=limit)
        stats = q.stats()
        return ok_response(
            data={
                "items": [
                    {
                        "decision_id": d.decision_id,
                        "subject": d.subject,
                        "confidence": d.confidence,
                        "reason": d.reason,
                        "status": d.status.value,
                        "priority": d.priority,
                        "review_by": d.review_by,
                        "created_at": d.created_at,
                    }
                    for d in items
                ],
                "stats": stats,
                "summary": q.product_summary(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/decision/review-queue/summary")
    @login_required
    def decision_review_summary():
        """Product metrics for workbench badge / profile."""
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        q = get_review_queue()
        summary = q.product_summary()
        top = q.list_pending(limit=5)
        return ok_response(
            data={
                **summary,
                "items": [
                    {
                        "decision_id": d.decision_id,
                        "subject": d.subject,
                        "confidence": d.confidence,
                        "reason": d.reason,
                        "priority": d.priority,
                        "review_by": d.review_by,
                        "created_at": d.created_at,
                    }
                    for d in top
                ],
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/<decision_id>/approve")
    @login_required
    def approve_decision(decision_id: str):
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        q = get_review_queue()
        dec = q.approve(decision_id)
        if not dec:
            raise ValidationError("decision_not_found")
        return ok_response(
            data={"decision_id": decision_id, "status": "approved"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/<decision_id>/reject")
    @login_required
    def reject_decision(decision_id: str):
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        q = get_review_queue()
        dec = q.reject(decision_id)
        if not dec:
            raise ValidationError("decision_not_found")
        return ok_response(
            data={"decision_id": decision_id, "status": "rejected"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/<decision_id>/correct")
    @login_required
    def correct_decision(decision_id: str):
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        q = get_review_queue()
        body = request.get_json(silent=True) or {}
        correction = q.add_correction(
            decision_id=decision_id,
            user_id=runtime.user_id(),
            target_phase=str(body.get("target_phase", "conclusion")),
            action=str(body.get("action", "override_conclusion")),
            payload=body.get("payload", {}),
            comment=str(body.get("comment", "")),
        )
        if not correction:
            raise ValidationError("decision_not_found")
        return ok_response(
            data={
                "decision_id": decision_id,
                "correction_id": correction.correction_id,
                "status": "corrected",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
