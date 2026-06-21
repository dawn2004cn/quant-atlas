from __future__ import annotations
"""API v1: Workflow status & lifecycle routes."""


import uuid
from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...application.workflows import WorkflowService
from ...core.registry import register_routes
from ...domain.enums import MarketCode
from .common import ok_resource, ok_response
from .v1_context import ApiV1Context
from .decorators import require_role


@register_routes(name="workflow", context="research", description="Workflow status & lifecycle routes")
def register_workflow_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    wf_service = ctx.workflow_service or WorkflowService()
    ctx.workflow_service = wf_service

    @blueprint.get("/workflows")
    @login_required
    def workflow_list():
        return ok_response(
            data={"workflows": wf_service.list_workflows()},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/workflows/<workflow_id>")
    @login_required
    def workflow_status(workflow_id: str):
        status = wf_service.get_status(workflow_id)
        if status is None:
            raise ValidationError(f"workflow_not_found: {workflow_id}")
        evidence = wf_service.get_evidence(workflow_id)
        return ok_response(
            data={"status": status, "evidence": evidence},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/workflows/research")
    @login_required
    @require_role("can_manage_users")
    def workflow_start_research():
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or "").strip()
        market_raw = (body.get("market") or "CN").strip().upper()
        if not symbol:
            raise ValidationError("symbol_required")
        try:
            market = MarketCode(market_raw)
        except ValueError:
            raise ValidationError(f"invalid_market: {market_raw}")

        wf_id = f"research_{uuid.uuid4().hex[:12]}"
        wf = wf_service.create_research(workflow_id=wf_id, symbol=symbol, market=market)
        wf_id = wf.start()
        return ok_resource(
            resource={"workflow_id": wf_id, "workflow_type": "research"},
            resource_key="workflow",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/workflows/trading")
    @login_required
    @require_role("can_manage_users")
    def workflow_start_trading():
        body = request.get_json(silent=True) or {}
        symbol = (body.get("symbol") or "").strip()
        market_raw = (body.get("market") or "CN").strip().upper()
        strategy = (body.get("strategy") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")
        try:
            market = MarketCode(market_raw)
        except ValueError:
            raise ValidationError(f"invalid_market: {market_raw}")

        wf_id = f"trade_{uuid.uuid4().hex[:12]}"
        wf = wf_service.create_trading(workflow_id=wf_id, symbol=symbol, market=market, strategy_name=strategy)
        wf_id = wf.start()
        return ok_resource(
            resource={"workflow_id": wf_id, "workflow_type": "trading"},
            resource_key="workflow",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/workflows/data-pipeline")
    @login_required
    @require_role("can_manage_users")
    def workflow_start_pipeline():
        body = request.get_json(silent=True) or {}
        name = (body.get("name") or "data_pipeline").strip()
        symbols = body.get("symbols") or []

        wf_id = f"pipeline_{uuid.uuid4().hex[:12]}"
        wf = wf_service.create_data_pipeline(workflow_id=wf_id, pipeline_name=name, symbols=symbols)
        wf_id = wf.start()
        return ok_resource(
            resource={"workflow_id": wf_id, "workflow_type": "data_pipeline"},
            resource_key="workflow",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/workflows/<workflow_id>/pause")
    @login_required
    def workflow_pause(workflow_id: str):
        if not wf_service.pause(workflow_id):
            raise ValidationError(f"workflow_not_found: {workflow_id}")
        return ok_resource(resource={"workflow_id": workflow_id, "status": "paused"}, resource_key="workflow", enable_legacy_alias=legacy)

    @blueprint.post("/workflows/<workflow_id>/cancel")
    @login_required
    def workflow_cancel(workflow_id: str):
        if not wf_service.cancel(workflow_id):
            raise ValidationError(f"workflow_not_found: {workflow_id}")
        return ok_resource(resource={"workflow_id": workflow_id, "status": "cancelled"}, resource_key="workflow", enable_legacy_alias=legacy)

    @blueprint.post("/workflows/<workflow_id>/resume")
    @login_required
    def workflow_resume(workflow_id: str):
        body = request.get_json(silent=True) or {}
        approved = body.get("approved", True)
        feedback = (body.get("feedback") or "").strip() or None
        result = wf_service.resume(workflow_id, approved=approved, feedback=feedback)
        if result is None:
            raise ValidationError(f"workflow_not_found: {workflow_id}")
        return ok_resource(resource={"workflow_id": workflow_id, "status": "resumed", "data": result}, resource_key="workflow", enable_legacy_alias=legacy)

    @blueprint.post("/workflows/<workflow_id>/human-intervention")
    @login_required
    def workflow_human(workflow_id: str):
        body = request.get_json(silent=True) or {}
        message = (body.get("message") or "").strip()
        if not message:
            raise ValidationError("message_required")
        if not wf_service.request_human_intervention(workflow_id, message):
            raise ValidationError(f"workflow_not_found: {workflow_id}")
        return ok_resource(resource={"workflow_id": workflow_id, "status": "waiting_human"}, resource_key="workflow", enable_legacy_alias=legacy)

    @blueprint.get("/workflows/<workflow_id>/stream")
    @login_required
    def workflow_stream(workflow_id: str):
        from flask import stream_with_context, Response


        def _yield_refresh_evoke_id():
            try:
                status = wf_service.get_status(workflow_id)
                evidence = wf_service.get_evidence(workflow_id) or []
                chosen = [getattr(item, "model_dump", lambda: ({}))() if hasattr(item, "model_dump") else dict(item) if not isinstance(item, str) else {"message": item} for item in evidence]
                chosen = [x for x in chosen if isinstance(x, dict)]
                head = chosen[-3:] if chosen else [{"stage": "refresh"}]
                head_text = "\n[stream] " + " | ".join(str((item.get("message") or item.get("event_type") or item.get("stage") or "event" )) for item in head)
                return head_text
            except Exception as exc:
                return f"\n[stream] ev_ok status_refresh {exc}"

        def _unpack_evidence(item):
            if hasattr(item, "model_dump"):
                try:
                    return item.model_dump()
                except Exception:
                    logger.warning("Suppressed exception", exc_info=True)
                    pass
            if isinstance(item, dict):
                return item
            if isinstance(item, str):
                return {"message": item}
            return dict(item)

        def event_stream():
            try:
                status = wf_service.get_status(workflow_id)
                if status is None:
                    yield f"event: error\ndata: {workflow_id}\n\n"
                    return
                evidence = wf_service.get_evidence(workflow_id) or []
                payload = [_unpack_evidence(item) for item in evidence]
                history = payload[-8:] if payload else [{"stage": "init"}]
                head_text = " | ".join(str((x.get("message") or x.get("event_type") or x.get("stage") or "event")) for x in history)
                yield f"event: history\ndata: {head_text}\n\n"
                yield f"event: start\ndata: {workflow_id} {str(status.head).replace(' ', '-')} stage\n\n"
                cur = status
                max_steps = 26
                for step_idx in range(max_steps):
                    try:
                        cur = wf_service.get_status(workflow_id)
                    except Exception:
                        yield f"event: heartbeat\ndata: step:{step_idx+1}\n\n"
                        continue
                    yield f"event: heartbeat\ndata: {(cur.stage or 'running')}\n\n"
                    if str(cur.head) in {"completed", "halted", "failed", "cancelled", "timeout"}:
                        yield f"event: complete\ndata: {str(cur.head).replace(' ', '-')}\n\n"
                        return
                    try:
                        scroll = wf_service.get_evidence(workflow_id) or []
                        prepended = [_unpack_evidence(item) for item in scroll[-4:]] if scroll else []
                        new_events = []
                        for item in reversed(prepended):
                            if item not in new_events:
                                new_events.insert(0, item)
                        text = "\n[stream] " + "\n[stream] ".join(str((x.get("message") or x.get("event_type") or x.get("stage") or "event")) for x in new_events)
                        yield f"event: progress\ndata: step {step_idx + 1}\n\n"
                        yield f"event: log\ndata: {text}\n\n"
                    except Exception:
                        yield f"event: log\ndata: \n[stream] step {step_idx + 1}\n\n"
                yield f"event: end_of_stream\ndata: max_frames\n\n"
            except Exception as exc:
                yield f"event: error\ndata: {exc}\n\n"
        return Response(stream_with_context(event_stream()), mimetype="text/event-stream")

    @blueprint.get("/workflows/optimizer-summary")
    @login_required
    def workflow_optimizer_summary():
        return ok_response(
            data={"optimizer": wf_service.get_optimizer_summary()},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
