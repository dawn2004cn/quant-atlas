"""Strategy synthesis parse, compile and preview routes."""

from __future__ import annotations

import logging

from flask import Blueprint, request

from app.application.errors import ExternalServiceError, ValidationError
from app.domain.strategies.strategy_synthesizer_models import LanguageTarget, StrategySpec
from app.presentation.api.common import ok_response
from app.presentation.api.v1.strategy_synthesis.runtime import StrategySynthesisRuntime
from app.presentation.api.v1_context import ApiV1Context

logger = logging.getLogger(__name__)


def register_strategy_synthesis_pipeline_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
    *,
    runtime: StrategySynthesisRuntime,
) -> None:
    _ = ctx

    @blueprint.route("/parse", methods=["POST"])
    def parse_strategy():
        """Parse natural language into a StrategySpec AST."""
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "") or "").strip()
        if not query:
            raise ValidationError("query_required")

        svc = runtime.synthesizer
        if svc is None:
            return runtime.unavailable_response()

        try:
            spec = svc.parse_strategy_intent(query)
            if spec is None:
                return ok_response(
                    data={"spec": None, "hint": "未识别到策略意图，请使用包含买入/卖出/止损/止盈的描述"},
                )
            return ok_response(data={"spec": spec.to_dict()})
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("strategy_synthesis.parse failed")
            raise ExternalServiceError(
                "parse_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/compile", methods=["POST"])
    def compile_strategy():
        """Compile a StrategySpec AST to target language code."""
        data = request.get_json(silent=True) or {}
        spec_dict = data.get("spec")
        if not spec_dict:
            raise ValidationError("spec_required")

        target_str = str(data.get("target", "python")).lower()
        try:
            target = LanguageTarget(target_str)
        except ValueError as exc:
            raise ValidationError(f"invalid_target: {target_str}") from exc

        svc = runtime.synthesizer
        if svc is None:
            return runtime.unavailable_response()

        try:
            spec = StrategySpec.from_dict(spec_dict)
            code = svc.compile_to_language(spec, target)
            return ok_response(data={"code": code, "target": target.value})
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("strategy_synthesis.compile failed")
            raise ExternalServiceError(
                "compile_failed",
                details={"reason": str(exc)},
            ) from exc

    @blueprint.route("/preview", methods=["POST"])
    def preview_full_pipeline():
        """Full pipeline: NL → AST → compile → evidence card."""
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "") or "").strip()
        if not query:
            raise ValidationError("query_required")

        svc = runtime.synthesizer
        if svc is None:
            return runtime.unavailable_response()

        try:
            result = svc.preview_full_pipeline(query)
            return ok_response(data=result)
        except ValidationError:
            raise
        except Exception as exc:
            logger.exception("strategy_synthesis.preview failed")
            raise ExternalServiceError(
                "preview_failed",
                details={"reason": str(exc)},
            ) from exc
