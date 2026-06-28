"""Safe expression parser for alpha factor expressions.

Replaces dangerous eval() calls with AST-based validation and evaluation.
"""

from __future__ import annotations

import ast
from typing import Any

_ALLOWED_NODE_TYPES: frozenset[type[ast.AST]] = frozenset({
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Attribute,
    ast.Subscript,
    ast.Slice,
    ast.List,
    ast.Tuple,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.Is, ast.IsNot, ast.In, ast.NotIn,
    ast.And, ast.Or,
    ast.USub, ast.UAdd, ast.Not, ast.Invert,
    ast.Pass,
})


class ExpressionSecurityError(ValueError):
    """Raised when an expression fails security validation."""


def _validate_node(node: ast.AST) -> None:
    """Recursively validate an AST node against the security whitelist."""
    if type(node) not in _ALLOWED_NODE_TYPES:
        raise ExpressionSecurityError(
            f"Node type {type(node).__name__} is not allowed. "
            f"Allowed: {', '.join(t.__name__ for t in sorted(_ALLOWED_NODE_TYPES, key=lambda t: t.__name__))}"
        )
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("_"):
            raise ExpressionSecurityError(f"Method calls starting with '_' not allowed: '{node.func.attr}'")
        if isinstance(node.func, ast.Name) and node.func.id.startswith("_"):
            raise ExpressionSecurityError(f"Function calls starting with '_' not allowed: '{node.func.id}'")
        if node.keywords:
            raise ExpressionSecurityError("Keyword arguments are not allowed in expressions")
    if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
        raise ExpressionSecurityError(f"Attribute access starting with '_' not allowed: '{node.attr}'")
    for child in ast.iter_child_nodes(node):
        _validate_node(child)


def parse_expression(expression: str) -> ast.AST:
    """Parse and validate a factor expression string."""
    tree = ast.parse(expression, mode="eval")
    if not isinstance(tree, ast.Expression):
        raise ExpressionSecurityError("Expression must be a valid Python expression")
    _validate_node(tree)
    return tree


def evaluate_expression(expression: str, local_dict: dict[str, Any]) -> Any:
    """Safely evaluate an expression string with restricted globals."""
    tree = parse_expression(expression)
    try:
        code = compile(tree, "<expression>", "eval")
        return eval(code, {"__builtins__": {}}, local_dict)
    except Exception as exc:
        raise ExpressionSecurityError(f"Expression evaluation failed: {exc}") from exc
