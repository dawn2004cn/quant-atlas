from __future__ import annotations

"""Safe genetic-programming expression evaluator (gplearn-style, no eval)."""

import math
import re
from collections.abc import Mapping, Sequence

UNARY_OPS = frozenset({"sqrt", "square", "log", "neg", "abs"})
BINARY_OPS = frozenset({"add", "sub", "mul", "div", "max", "min", "avg"})
_TOKEN = re.compile(r"\s*(?:([A-Za-z_][A-Za-z0-9_]*)|(-?\d+(?:\.\d+)?)|(\()|(\))|(,))")


class ExpressionError(ValueError):
    """Invalid or unsafe factor expression."""


def features_from_returns(returns: Sequence[float], n_features: int = 6) -> dict[str, list[float]]:
    """Bind x0..x5 from a return series so GP expressions can be evaluated."""
    r = [float(x) for x in returns]
    n = len(r)
    feats: dict[str, list[float]] = {"x0": r}
    if n_features > 1:
        feats["x1"] = [0.0, *r[:-1]] if n else []
    if n_features > 2:
        lag = 5
        feats["x2"] = ([0.0] * min(lag, n) + r[:-lag]) if n > lag else [0.0] * n
    if n_features > 3:
        feats["x3"] = _rolling_mean(r, 5)
    if n_features > 4:
        feats["x4"] = _rolling_mean(r, 10)
    if n_features > 5:
        feats["x5"] = [1.0 if x > 0 else (-1.0 if x < 0 else 0.0) for x in r]
    return feats


def evaluate_expression(expr: str, features: Mapping[str, Sequence[float]]) -> list[float]:
    """Evaluate a factor tree such as ``add(x0,mul(x1,2))`` against feature series."""
    if not isinstance(expr, str) or not expr.strip():
        raise ExpressionError("expression is required")
    if not features:
        raise ExpressionError("features are required")
    lengths = {len(v) for v in features.values()}
    if len(lengths) != 1:
        raise ExpressionError("all features must have the same length")
    n = lengths.pop()
    bound = {k: [float(x) for x in v] for k, v in features.items()}
    tokens = _tokenize(expr)
    value, pos = _parse(tokens, 0, bound, n)
    if tokens[pos][0] != "eof":
        raise ExpressionError("trailing tokens in expression")
    return _as_vec(value, n)


def _rolling_mean(xs: list[float], window: int) -> list[float]:
    out = [0.0] * len(xs)
    if window <= 0:
        return out
    total = 0.0
    for i, val in enumerate(xs):
        total += val
        if i >= window:
            total -= xs[i - window]
        count = window if i >= window - 1 else (i + 1)
        out[i] = total / count
    return out


def _tokenize(expr: str) -> list[tuple[str, str | float | None]]:
    tokens: list[tuple[str, str | float | None]] = []
    pos = 0
    for match in _TOKEN.finditer(expr):
        if expr[pos:match.start()].strip():
            raise ExpressionError(f"invalid token at {pos}")
        pos = match.end()
        ident, number, lparen, rparen, comma = match.groups()
        if ident:
            tokens.append(("id", ident))
        elif number is not None:
            tokens.append(("num", float(number)))
        elif lparen:
            tokens.append(("lparen", "("))
        elif rparen:
            tokens.append(("rparen", ")"))
        else:
            tokens.append(("comma", ","))
    if expr[pos:].strip():
        raise ExpressionError("trailing garbage in expression")
    tokens.append(("eof", None))
    return tokens


def _parse(
    tokens: list[tuple[str, str | float | None]],
    pos: int,
    features: Mapping[str, list[float]],
    n: int,
) -> tuple[list[float] | float, int]:
    kind, payload = tokens[pos]
    if kind == "num":
        return float(payload), pos + 1
    if kind != "id":
        raise ExpressionError("expected identifier or number")
    name = str(payload)
    nxt = tokens[pos + 1][0] if pos + 1 < len(tokens) else "eof"
    if nxt != "lparen":
        if name not in features:
            raise ExpressionError(f"unknown identifier: {name}")
        return features[name], pos + 1
    if name not in UNARY_OPS and name not in BINARY_OPS:
        raise ExpressionError(f"unknown identifier: {name}")
    pos += 2
    args: list[list[float] | float] = []
    if tokens[pos][0] != "rparen":
        arg, pos = _parse(tokens, pos, features, n)
        args.append(arg)
        while tokens[pos][0] == "comma":
            arg, pos = _parse(tokens, pos + 1, features, n)
            args.append(arg)
    if tokens[pos][0] != "rparen":
        raise ExpressionError("expected ')'")
    return _apply(name, args, n), pos + 1


def _as_vec(value: list[float] | float, n: int) -> list[float]:
    if isinstance(value, list):
        if len(value) != n:
            raise ExpressionError("feature length mismatch")
        return value
    return [float(value)] * n


def _apply(name: str, args: list[list[float] | float], n: int) -> list[float]:
    if name in UNARY_OPS:
        if len(args) != 1:
            raise ExpressionError(f"{name} expects 1 argument")
        xs = _as_vec(args[0], n)
        return [_unary(name, x) for x in xs]
    if len(args) != 2:
        raise ExpressionError(f"{name} expects 2 arguments")
    left = _as_vec(args[0], n)
    right = _as_vec(args[1], n)
    return [_binary(name, a, b) for a, b in zip(left, right)]


def _unary(name: str, x: float) -> float:
    if name == "neg":
        return -x
    if name == "abs":
        return abs(x)
    if name == "square":
        return x * x
    if name == "sqrt":
        return math.sqrt(x) if x >= 0 else float("nan")
    if name == "log":
        return math.log(x) if x > 0 else float("nan")
    raise ExpressionError(f"unknown identifier: {name}")


def _binary(name: str, a: float, b: float) -> float:
    if name == "add":
        return a + b
    if name == "sub":
        return a - b
    if name == "mul":
        return a * b
    if name == "div":
        return a / b if abs(b) > 1e-15 else float("nan")
    if name == "max":
        return a if a >= b else b
    if name == "min":
        return a if a <= b else b
    if name == "avg":
        return (a + b) / 2.0
    raise ExpressionError(f"unknown identifier: {name}")
