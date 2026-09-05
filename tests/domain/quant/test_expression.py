"""Safe GP expression evaluator — no eval/exec."""

from __future__ import annotations

import math

import pytest

from app.domain.quant.expression import evaluate_expression, features_from_returns


def test_add_and_mul():
    out = evaluate_expression("mul(add(x0,x1),x0)", {"x0": [1.0, 2.0], "x1": [3.0, 4.0]})
    assert out == [4.0, 12.0]


def test_unary_and_scalar_broadcast():
    out = evaluate_expression("add(square(x0),2)", {"x0": [3.0, 4.0]})
    assert out == [11.0, 18.0]


def test_div_by_zero_is_nan():
    out = evaluate_expression("div(x0,x1)", {"x0": [1.0], "x1": [0.0]})
    assert math.isnan(out[0])


def test_rejects_unknown_identifier():
    with pytest.raises(ValueError):
        evaluate_expression("__import__('os')", {"x0": [1.0]})


def test_rejects_eval_style_payload():
    with pytest.raises(ValueError):
        evaluate_expression("eval(x0)", {"x0": [1.0]})


def test_features_from_returns_binds_x0_to_returns():
    rets = [0.01, -0.02, 0.03]
    feats = features_from_returns(rets)
    assert feats["x0"] == rets
    assert len(feats["x1"]) == 3
