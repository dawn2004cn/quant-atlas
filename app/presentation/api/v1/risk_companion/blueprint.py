"""Nested blueprint for risk companion routes."""

from __future__ import annotations

from flask import Blueprint

risk_companion_blueprint = Blueprint("risk_companion", __name__, url_prefix="/risk/companion")
