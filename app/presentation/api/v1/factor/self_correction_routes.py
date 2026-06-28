"""Factor self-correction tracking routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_resource
from app.presentation.api.v1_context import ApiV1Context

from ...decorators import require_role, service_fallback


def register_factor_self_correction_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    @blueprint.post("/factor/self-correction/record")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_self_correction_service")
    def factor_record_performance():
        svc = getattr(ctx, "factor_self_correction_service", None)
        body = request.get_json(silent=True) or {}
        factor_name = body.get("factor_name", "").strip()
        period = body.get("period", "").strip()
        if not factor_name or not period:
            raise ValidationError("factor_name_and_period_required")

        svc.record_factor_performance(
            factor_name=factor_name,
            period=period,
            ic=float(body.get("ic", 0)),
            icir=float(body.get("icir", 0)),
            return_pct=float(body.get("return_pct", 0)),
        )
        return ok_resource(
            resource={"recorded": True, "factor_name": factor_name},
            resource_key="factor_record",
            enable_legacy_alias=False,
        )

    @blueprint.get("/factor/self-correction/analyze")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_self_correction_service")
    def factor_analyze_degradation():
        svc = getattr(ctx, "factor_self_correction_service", None)
        factor_name = request.args.get("factor_name", "").strip()
        if not factor_name:
            raise ValidationError("factor_name_required")
        return ok_resource(
            resource=svc.analyze_factor_degradation(factor_name),
            resource_key="factor_analysis",
            enable_legacy_alias=False,
        )

    @blueprint.get("/factor/self-correction/prompt")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_self_correction_service")
    def factor_prompt_improvement():
        svc = getattr(ctx, "factor_self_correction_service", None)
        factor_name = request.args.get("factor_name", "").strip()
        if not factor_name:
            raise ValidationError("factor_name_required")
        analysis = svc.analyze_factor_degradation(factor_name)
        prompt = svc.generate_prompt_improvement(factor_name, analysis)
        return ok_resource(
            resource={"factor_name": factor_name, "prompt_improvement": prompt},
            resource_key="prompt_improvement",
            enable_legacy_alias=False,
        )

    @blueprint.get("/factor/self-correction/status")
    @login_required
    @require_role("can_manage_users")
    @service_fallback("factor_self_correction_service")
    def factor_all_status():
        svc = getattr(ctx, "factor_self_correction_service", None)
        return ok_resource(
            resource={"factors": svc.get_all_factors_status()},
            resource_key="factor_status",
            enable_legacy_alias=False,
        )
