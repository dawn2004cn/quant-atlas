"""Feature Pipeline train / latest registry API."""

from __future__ import annotations

import json
from pathlib import Path

from flask import Blueprint, request

from app.core.registry import register_routes
from app.presentation.api.responses import error_response, success_response


def _models_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "instance" / "feature_models"


@register_routes(name="feature_pipeline", context="data", description="Feature pipeline train / registry")
def register_feature_pipeline_routes(blueprint, ctx=None) -> None:
    _ = ctx
    bp = Blueprint("feature_pipeline", __name__, url_prefix="/data/feature-pipeline")

    @bp.get("/latest")
    def feature_pipeline_latest():
        spec = (request.args.get("spec") or "cn_day_v0").strip()
        path = _models_dir() / f"{spec}_latest.json"
        if not path.exists():
            return error_response("feature_model_not_found", code=404)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return error_response(f"feature_model_corrupt:{exc}", code=500)
        return success_response({"path": str(path), "registry": data})

    @bp.post("/train")
    def feature_pipeline_train():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            body = {}
        from app.tasks.feature_pipeline_tasks import run_feature_pipeline_tick

        result = run_feature_pipeline_tick(
            spec_name=str(body.get("spec_name") or "cn_day_v0"),
            model_backend=body.get("model_backend"),
            symbol=body.get("symbol"),
            prefer_live_bars=bool(body.get("prefer_live_bars", True)),
        )
        return success_response(result)

    @bp.post("/predict")
    def feature_pipeline_predict():
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            body = {}
        from app.domain.alpha.feature_pipeline_predict import predict_symbol

        result = predict_symbol(
            symbol=body.get("symbol"),
            spec_name=str(body.get("spec_name") or "cn_day_v0"),
            prefer_live_bars=bool(body.get("prefer_live_bars", True)),
        )
        if not result.get("ok"):
            return error_response(str(result.get("error") or "predict_failed"), code=400)
        return success_response(result)

    @bp.get("/predict")
    def feature_pipeline_predict_get():
        from app.domain.alpha.feature_pipeline_predict import predict_symbol

        result = predict_symbol(
            symbol=request.args.get("symbol"),
            spec_name=str(request.args.get("spec") or "cn_day_v0"),
            prefer_live_bars=True,
        )
        if not result.get("ok"):
            return error_response(str(result.get("error") or "predict_failed"), code=400)
        return success_response(result)

    blueprint.register_blueprint(bp)
