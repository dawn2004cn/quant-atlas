"""Nested blueprint for provenance explorer routes."""

from __future__ import annotations

from flask import Blueprint

provenance_blueprint = Blueprint("provenance_explorer", __name__, url_prefix="/provenance")
