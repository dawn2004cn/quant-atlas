"""Self-Healing Execution API routes (10.0)."""

from __future__ import annotations

import asyncio
from typing import Any

from flask import Blueprint, jsonify, request

from app.core.logger import get_logger
from app.core.registry import register_routes
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def _service_unavailable():
    payload = error_payload(ErrorCode.SERVICE_UNAVAILABLE, "service_not_available")
    return jsonify(payload), ErrorCode.SERVICE_UNAVAILABLE.http_status


def _internal_error(exc: Exception):
    logger.error("%s", exc)
    payload = error_payload(ErrorCode.INTERNAL_ERROR, str(exc))
    return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status


def _validation_error(message: str):
    payload = error_payload(ErrorCode.VALIDATION_ERROR, message)
    return jsonify(payload), ErrorCode.VALIDATION_ERROR.http_status


def _run_async(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@register_routes(
    name="self_healing_execution",
    context="execution",
    description="Self-Healing Execution API (10.0)",
    depends_on=["self_healing_execution_service"],
)
def register_self_healing_execution_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    """Register self-healing execution routes."""

    @blueprint.route("/execution/self-healing/manifest", methods=["GET"])
    def get_manifest():
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            return success_response(data=service.get_manifest())
        except Exception as exc:
            return _internal_error(exc)

    @blueprint.route("/execution/self-healing/venues", methods=["GET"])
    def get_venue_stats():
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            return success_response(data=service.get_venue_stats())
        except Exception as exc:
            return _internal_error(exc)

    @blueprint.route("/execution/self-healing/submit", methods=["POST"])
    def submit_order():
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            body = request.get_json()
            if not body:
                return _validation_error("request_body_required")
            result = _run_async(service.submit_order(**body))
            if isinstance(result, dict) and result.get("ok") is False:
                payload = error_payload(ErrorCode.SERVICE_ERROR, str(result.get("error", "submit_failed")))
                return jsonify(payload), ErrorCode.SERVICE_ERROR.http_status
            return success_response(data=result)
        except Exception as exc:
            return _internal_error(exc)

    @blueprint.route("/execution/self-healing/log", methods=["GET"])
    def get_execution_log():
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            symbol = request.args.get("symbol")
            limit = int(request.args.get("limit", 100))
            log = service.get_execution_log(symbol=symbol, limit=limit)
            return success_response(data={"log": log, "count": len(log)})
        except Exception as exc:
            return _internal_error(exc)

    @blueprint.route("/execution/self-healing/venue/<venue_id>/reset", methods=["POST"])
    def reset_venue(venue_id: str):
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            result = service.reset_venue(venue_id)
            if isinstance(result, dict) and not result.get("ok"):
                payload = error_payload(ErrorCode.NOT_FOUND, str(result.get("error", "venue_not_found")))
                return jsonify(payload), ErrorCode.NOT_FOUND.http_status
            return success_response(data=result)
        except Exception as exc:
            return _internal_error(exc)

    @blueprint.route("/execution/self-healing/health-check", methods=["POST"])
    def health_check_all():
        service = ctx.self_healing_execution_service
        if service is None:
            return _service_unavailable()
        try:
            result = _run_async(service.health_check_all())
            return success_response(data=result)
        except Exception as exc:
            return _internal_error(exc)
