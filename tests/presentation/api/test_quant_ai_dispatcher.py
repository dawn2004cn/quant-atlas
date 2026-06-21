"""Quant AI dispatcher smoke import."""

from __future__ import annotations


def test_quant_ai_submodules_export_register_functions():
    from app.presentation.api.v1.quant_ai import (
        register_quant_ai_analysis_routes,
        register_quant_ai_llm_routes,
        register_quant_ai_prediction_routes,
        register_quant_ai_selection_routes,
        register_quant_ai_strategy_routes,
    )

    for fn in (
        register_quant_ai_analysis_routes,
        register_quant_ai_llm_routes,
        register_quant_ai_prediction_routes,
        register_quant_ai_selection_routes,
        register_quant_ai_strategy_routes,
    ):
        assert callable(fn)


def test_quant_ai_dispatcher_registers():
    from app.presentation.api.routes_v1_quant_ai import register_quant_ai_routes

    assert callable(register_quant_ai_routes)
