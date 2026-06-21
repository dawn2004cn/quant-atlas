"""Decision provenance, trace, feedback and review routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response
from app.presentation.api.v1.decision_provenance.runtime import DecisionProvenanceRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_decision_lifecycle_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: DecisionProvenanceRuntime,
) -> None:
    legacy = runtime.legacy

    @blueprint.post("/decision/provenance")
    @login_required
    def decision_provenance():
        """Create a replayable decision context from AI/strategy output."""
        from app.modules.system.services.ui.decision_provenance_service import (
            DecisionProvenanceService,
        )

        body = request.get_json(silent=True) or {}
        subject = (body.get("subject") or body.get("symbol") or "").strip()
        if not subject:
            raise ValidationError("subject_required")
        payload = DecisionProvenanceService().build_context(
            subject=subject,
            input_snapshot=body.get("input_snapshot") if isinstance(body.get("input_snapshot"), dict) else {},
            model_version=str(body.get("model_version") or "unknown"),
            reasoning_trace=body.get("reasoning_trace") if isinstance(body.get("reasoning_trace"), list) else [],
            evidence=body.get("evidence") if isinstance(body.get("evidence"), list) else [],
        )
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/decision/trace/<decision_id>")
    @login_required
    def decision_trace_get(decision_id: str):
        """Fetch a recorded decision trace by ``decision_id``."""
        from app.modules.system.services.ui.decision_trace_service import (
            get_decision_trace_service,
        )

        trace = get_decision_trace_service().trace_payload(decision_id.strip())
        if trace is None:
            raise ValidationError(
                "decision_trace_not_found",
                details={"decision_id": decision_id},
            )
        return ok_response(
            data=trace,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/feedback")
    @login_required
    def decision_feedback_submit():
        """Submit thumbs-up/down feedback on an AI decision trace."""
        from app.application.errors import ValidationError as AppValidationError
        from app.core.middleware.request_context import require_authenticated_user_id
        from app.modules.ai_agent.services.ai.decision_feedback_service import (
            DecisionFeedbackService,
            configure_decision_feedback_service,
            get_decision_feedback_service,
        )

        body = request.get_json(silent=True) or {}
        decision_id = str(body.get("decision_id") or "").strip()
        rating = str(body.get("rating") or "").strip().lower()
        if not decision_id:
            raise ValidationError("decision_id_required")
        knowledge = getattr(ctx, "user_knowledge_service", None)
        prompt_evolution = getattr(ctx, "prompt_evolution_service", None)
        if knowledge is not None or prompt_evolution is not None:
            configure_decision_feedback_service(
                DecisionFeedbackService(
                    user_knowledge_service=knowledge,
                    prompt_evolution_service=prompt_evolution,
                )
            )
        svc = get_decision_feedback_service()
        try:
            dto = svc.submit(
                user_id=require_authenticated_user_id(),
                decision_id=decision_id,
                rating=rating,
                reasoning_path_id=body.get("reasoning_path_id"),
                comment=str(body.get("comment") or ""),
            )
        except ValueError as exc:
            raise AppValidationError("invalid_feedback", details={"reason": str(exc)}) from exc
        return ok_response(
            data=dto.model_dump(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/decision/review-queue")
    @login_required
    def decision_review_list():
        """List pending decisions awaiting human review."""
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        limit = min(int(request.args.get("limit", 50)), 100)
        queue = get_review_queue()
        pending = queue.list_pending(limit=limit)
        return ok_response(
            data={
                "items": [
                    {
                        "decision_id": d.decision_id,
                        "subject": d.subject,
                        "confidence": d.confidence,
                        "reason": d.reason,
                        "status": d.status.value,
                        "created_at": d.created_at,
                        "corrections_count": len(d.corrections),
                    }
                    for d in pending
                ],
                "stats": queue.stats(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/decision/<decision_id>/correct")
    @login_required
    def decision_correct(decision_id: str):
        """Submit a user correction to a pending decision's reasoning trace."""
        from app.application.errors import ValidationError as AppValidationError
        from app.core.middleware.request_context import require_authenticated_user_id
        from app.modules.system.services.ui.decision_review_queue import get_review_queue

        body = request.get_json(silent=True) or {}
        target_phase = str(body.get("target_phase") or "").strip()
        action = str(body.get("action") or "").strip()
        if not target_phase or not action:
            raise AppValidationError("target_phase and action are required")

        queue = get_review_queue()
        correction = queue.add_correction(
            decision_id=decision_id.strip(),
            user_id=require_authenticated_user_id(),
            target_phase=target_phase,
            action=action,
            payload=body.get("payload") or {},
            comment=str(body.get("comment") or ""),
        )
        if correction is None:
            raise AppValidationError(
                "decision_not_found",
                details={"decision_id": decision_id},
            )
        return ok_response(
            data={
                "correction_id": correction.correction_id,
                "decision_id": correction.decision_id,
                "action": correction.action,
                "target_phase": correction.target_phase,
                "created_at": correction.created_at,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
