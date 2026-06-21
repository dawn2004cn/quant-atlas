"""Nested blueprint for strategy synthesis routes."""

from __future__ import annotations

from flask import Blueprint

strategy_synthesis_blueprint = Blueprint(
    "strategy_synthesis",
    __name__,
    url_prefix="/strategy-synthesis",
)
