"""Quant/AI API sub-package."""

from app.presentation.api.v1.quant_ai.analysis_routes import register_quant_ai_analysis_routes
from app.presentation.api.v1.quant_ai.llm_routes import register_quant_ai_llm_routes
from app.presentation.api.v1.quant_ai.prediction_routes import register_quant_ai_prediction_routes
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime
from app.presentation.api.v1.quant_ai.selection_routes import register_quant_ai_selection_routes
from app.presentation.api.v1.quant_ai.strategy_routes import register_quant_ai_strategy_routes

__all__ = [
    "QuantAiRuntime",
    "register_quant_ai_analysis_routes",
    "register_quant_ai_llm_routes",
    "register_quant_ai_prediction_routes",
    "register_quant_ai_selection_routes",
    "register_quant_ai_strategy_routes",
]
