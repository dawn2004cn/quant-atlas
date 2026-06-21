"""Nested blueprint for one-click routes."""

from __future__ import annotations

from flask import Blueprint

one_click_blueprint = Blueprint("one_click", __name__, url_prefix="/one-click")
