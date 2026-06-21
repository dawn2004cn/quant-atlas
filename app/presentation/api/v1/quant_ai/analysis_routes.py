"""AI analysis, research, and chat routes."""

from __future__ import annotations

import json

from flask import Blueprint, Response, request, stream_with_context
from flask_login import login_required

from app.application.errors import ValidationError
from app.application.request_executor import run_async
from app.core.logger import get_logger
from app.presentation.api.common import (
    ok_collection,
    ok_resource,
    ok_response,
    parse_market,
    require_expensive_ai_role,
)
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime, authenticated_user_id
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_quant_ai_analysis_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: QuantAiRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    ai_analysis_service = runtime.ai_analysis_service

    @blueprint.post("/ai/analyze")
    @login_required
    def ai_analyze():
        payload = request.get_json(silent=True) or {}
        symbol = (payload.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol is required")
        market = parse_market(payload.get("market", "CN"))
        user_hypothesis = (payload.get("user_hypothesis") or "").strip() or None
        hypothesis_id = (payload.get("hypothesis_id") or "").strip() or None
        result = ai_analysis_service.analyze(
            symbol,
            market,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )
        return ok_resource(
            resource=result,
            resource_key="analysis",
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ai/analyze/stream")
    @login_required
    def ai_analyze_stream():
        """SSE stream of AI reasoning evidence steps."""
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol is required")
        market = parse_market(request.args.get("market", "CN"))
        user_hypothesis = (request.args.get("user_hypothesis") or "").strip() or None
        hypothesis_id = (request.args.get("hypothesis_id") or "").strip() or None

        def generate():
            try:
                from app.infrastructure.realtime.websocket_adapter import (
                    broadcast_ai_analysis_chunk,
                )
            except ImportError:
                broadcast_ai_analysis_chunk = None  # type: ignore[assignment,misc]

            for chunk in ai_analysis_service.analyze_stream(
                symbol,
                market,
                user_hypothesis=user_hypothesis,
                hypothesis_id=hypothesis_id,
            ):
                if broadcast_ai_analysis_chunk is not None:
                    try:
                        payload = chunk if isinstance(chunk, dict) else {"data": chunk}
                        broadcast_ai_analysis_chunk(symbol, market.value, payload)
                    except Exception:
                        logger.debug("ai_analyze_stream socket broadcast skipped", exc_info=True)
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @blueprint.get("/ai/hypotheses")
    @login_required
    def ai_hypothesis_catalog():
        from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import (
            HypothesisEvaluationService,
        )

        items = [x.model_dump() for x in HypothesisEvaluationService().list_catalog()]
        return ok_response(
            data={"hypotheses": items},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/ai/report")
    @login_required
    def ai_report():
        payload = request.get_json(silent=True) or {}
        symbol = (payload.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol is required")
        market = parse_market(payload.get("market", "CN"))
        result = ai_analysis_service.analyze(symbol, market)
        report = {
            "symbol": symbol,
            "market": market.value,
            "summary": result.get("ai", {}).get("analysis", ""),
            "generated_at": result.get("generated_at", ""),
        }
        return ok_resource(
            resource=report,
            resource_key="report",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/ai/research")
    @login_required
    def ai_research():
        require_expensive_ai_role()
        payload = request.get_json(silent=True) or {}
        ticker = (payload.get("ticker") or "").strip()
        query = (payload.get("query") or "").strip()
        if not ticker:
            raise ValidationError("ticker is required")
        if not query:
            raise ValidationError("query is required")
        user_id = parse_int_param(payload.get("user_id"), name="user_id", min_value=1)
        if user_id != authenticated_user_id():
            raise ValidationError("user_id must match the logged-in user")
        llm_profile: dict | None = None
        raw_llm = payload.get("llm")
        if isinstance(raw_llm, dict) and str(raw_llm.get("provider") or "").strip():
            llm_profile = {
                "provider": str(raw_llm.get("provider") or "").strip().lower(),
                "api_key": str(raw_llm.get("api_key") or "").strip(),
                "model": str(raw_llm.get("model") or "").strip(),
                "base_url": (str(raw_llm.get("base_url") or "").strip() or None),
                "temperature": raw_llm.get("temperature", 0.2),
                "timeout_sec": raw_llm.get("timeout_sec", 120),
            }
        result = run_async(
            runtime.require_ai_research_service().run_research(
                ticker, query, user_id, llm_profile=llm_profile,
            )
        )
        return ok_resource(
            resource=result,
            resource_key="ai_research",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/ai/chat")
    @login_required
    def ai_chat():
        payload = request.get_json(silent=True) or {}
        message = (payload.get("message") or "").strip()
        thread_id = (payload.get("thread_id") or "").strip()
        if not message:
            raise ValidationError("message is required")
        user_id = authenticated_user_id()
        result = run_async(
            runtime.require_ai_research_service().run_chat(message, user_id, thread_id=thread_id or None)
        )
        return ok_resource(
            resource=result,
            resource_key="chat",
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/ai/chat/history")
    @login_required
    def ai_chat_history():
        user_id = authenticated_user_id()
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50)
        history = runtime.require_ai_research_service().get_chat_history(user_id, limit)
        return ok_collection(
            items=history,
            item_key="history",
            enable_legacy_alias=legacy,
        )

    @blueprint.delete("/ai/chat/history")
    @login_required
    def ai_chat_clear():
        user_id = authenticated_user_id()
        thread_id = (request.args.get("thread_id") or "").strip() or None
        runtime.require_ai_research_service().clear_chat_history(user_id, thread_id)
        return ok_response(data={"ok": True}, legacy_alias_key=None, enable_legacy_alias=legacy)
