"""因子表达式门禁（无 Qlib）。"""

from __future__ import annotations

from app.infrastructure.rdagent.factor_expression_gate import evaluate_factor_expression_gate


def test_gate_skipped_when_no_factor_task() -> None:
    r = evaluate_factor_expression_gate({"artifacts": []})
    assert r.get("skipped") is True


def test_gate_ok_with_formulation_and_ic() -> None:
    bundle = {
        "artifacts": [
            {
                "kind": "factor_task",
                "artifact_id": "run::r0::task::f",
                "round_index": 0,
                "factor_name": "m",
                "factor_formulation": "Mean($close, 5)",
                "metrics": {"ic_lag_1": 0.03},
            }
        ]
    }
    r = evaluate_factor_expression_gate(bundle)
    assert r.get("skipped") is False
    assert r.get("ok") is True
    assert r.get("ic_lag1") == 0.03


def test_gate_fail_empty_formulation() -> None:
    bundle = {
        "artifacts": [
            {
                "kind": "factor_task",
                "artifact_id": "run::r1::task::f",
                "round_index": 1,
                "factor_name": "empty",
                "factor_formulation": "   ",
                "metrics": {},
            }
        ]
    }
    r = evaluate_factor_expression_gate(bundle)
    assert r.get("ok") is False


def test_gate_fail_nonfinite_ic() -> None:
    bundle = {
        "artifacts": [
            {
                "kind": "factor_task",
                "artifact_id": "run::r0::task::f",
                "round_index": 0,
                "factor_formulation": "x",
                "metrics": {"ic_lag_1": float("nan")},
            }
        ]
    }
    r = evaluate_factor_expression_gate(bundle)
    assert r.get("ok") is False

