"""Prediction model routes."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_collection, ok_resource, parse_market
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime
from app.presentation.api.v1_context import ApiV1Context


def register_quant_ai_prediction_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: QuantAiRuntime,
) -> None:
    _ = ctx
    legacy = runtime.legacy
    prediction_service = runtime.prediction_service

    @blueprint.get("/predict/models")
    @login_required
    def predict_models_list():
        models = prediction_service.list_models()
        return ok_collection(
            items=models,
            item_key="models",
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/predict/scores")
    @login_required
    def predict_scores():
        body = request.get_json(silent=True) or {}
        raw_syms = body.get("symbols") or []
        if isinstance(raw_syms, str):
            raw_syms = [raw_syms]
        symbols = [str(s).strip() for s in raw_syms if str(s).strip()]
        if not symbols:
            raise ValidationError("symbols 必填(非空数组)")
        if len(symbols) > 120:
            raise ValidationError("symbols 最多 120 只")
        market = parse_market(body.get("market", "CN"))
        model_id = str(body.get("model_id") or body.get("model") or "").strip() or None
        horizon = parse_int_param(body.get("horizon_days"), name="horizon_days", default=20, min_value=5)
        out = prediction_service.scores_cross_section(symbols, market, model_id=model_id, horizon_days=horizon)
        return ok_resource(
            resource=out,
            resource_key="predict_scores",
            enable_legacy_alias=legacy,
        )
