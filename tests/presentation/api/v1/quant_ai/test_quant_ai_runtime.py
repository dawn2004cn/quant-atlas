"""Tests for QuantAiRuntime."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.application.errors import ValidationError
from app.presentation.api.route_deps import AiRouteDeps
from app.presentation.api.v1.quant_ai.runtime import QuantAiRuntime


def test_from_deps_maps_fields():
    deps = AiRouteDeps(
        strategy_service=object(),
        prediction_service=object(),
        selection_source_service=object(),
        ai_analysis_service=object(),
        ai_research_service=object(),
        rdagent_run_service=None,
        swarm_service=None,
        enable_legacy_response_fields=False,
        enable_qlib=True,
        task_message_store=None,
    )
    runtime = QuantAiRuntime.from_deps(deps)
    assert runtime.enable_qlib is True
    assert runtime.legacy is False


def test_require_strategy_service_raises_when_missing():
    runtime = QuantAiRuntime.from_deps(
        AiRouteDeps(
            strategy_service=None,
            prediction_service=None,
            selection_source_service=None,
            ai_analysis_service=None,
            ai_research_service=None,
            rdagent_run_service=None,
            swarm_service=None,
        )
    )
    with pytest.raises(ValidationError, match="strategy_service"):
        runtime.require_strategy_service()


def test_push_task_noop_without_store():
    runtime = QuantAiRuntime.from_deps(
        AiRouteDeps(
            strategy_service=None,
            prediction_service=None,
            selection_source_service=None,
            ai_analysis_service=None,
            ai_research_service=None,
            rdagent_run_service=None,
            swarm_service=None,
            task_message_store=None,
        )
    )
    runtime.push_task(event="x", task_name="t", detail="d", meta={})

    store = SimpleNamespace(pushed=[])

    def _push(**kwargs):
        store.pushed.append(kwargs)

    store.push = _push
    runtime2 = QuantAiRuntime.from_deps(
        AiRouteDeps(
            strategy_service=None,
            prediction_service=None,
            selection_source_service=None,
            ai_analysis_service=None,
            ai_research_service=None,
            rdagent_run_service=None,
            swarm_service=None,
            task_message_store=store,
        )
    )
    runtime2.push_task(event="done", task_name="inline.test", detail="ok", meta={"k": 1})
    assert len(store.pushed) == 1
    assert store.pushed[0]["event"] == "done"
