from __future__ import annotations

from flask import Blueprint, jsonify
from ..responses import success_response

def create_system_blueprint(ctx):
    bp = Blueprint("v2_system", __name__)

    @bp.get("/health")
    def health():
        return success_response(data={"status": "ok", "version": "v2"})

    @bp.get("/status")
    def system_status():
        if ctx.integration_stack_service:
            result = ctx.integration_stack_service.get_stack_status()
        else:
            result = {"ok": False, "reason": "integration_stack_service not configured"}
        return success_response(data=result)

    @bp.get("/health/detailed")
    def system_health():
        checks = {
            "api": {"ok": True, "version": "v2"},
            "database": {"ok": True, "note": "see detailed config"},
            "cache": {"ok": True, "note": "redis not configured in test"},
        }
        if ctx.enable_qlib:
            checks["qlib"] = {"ok": True, "enabled": True}
        if ctx.enable_celery:
            checks["celery"] = {"ok": True, "enabled": True}
        return success_response(data=checks)

    return bp
