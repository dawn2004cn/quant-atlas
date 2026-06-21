"""Shared helpers for attribution HTTP routes."""

from __future__ import annotations

from flask import request

DEFAULT_POSITIONS: list[dict] = [
    {"symbol": "600519", "name": "贵州茅台", "value": 200000, "return_pct": 5.2, "sector": "白酒"},
    {"symbol": "000858", "name": "五粮液", "value": 150000, "return_pct": 3.8, "sector": "白酒"},
    {"symbol": "300750", "name": "宁德时代", "value": 180000, "return_pct": -2.1, "sector": "新能源"},
]


def parse_positions_payload() -> list[dict]:
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        positions = body.get("positions")
        if isinstance(positions, list) and positions:
            return positions
    return DEFAULT_POSITIONS


def parse_factor_map(prefix: str) -> dict[str, float]:
    result: dict[str, float] = {}
    source = request.get_json(silent=True) or {} if request.method == "POST" else {}
    nested = source.get(f"{prefix}s") or source.get(prefix) or {}
    if isinstance(nested, dict):
        for key, val in nested.items():
            try:
                result[str(key)] = float(val) / 100.0 if abs(float(val)) > 1 else float(val)
            except (TypeError, ValueError):
                continue
    for key, val in request.args.items():
        marker = f"{prefix}_"
        if key.startswith(marker):
            try:
                result[key[len(marker) :]] = float(val) / 100.0
            except ValueError:
                continue
    return result
