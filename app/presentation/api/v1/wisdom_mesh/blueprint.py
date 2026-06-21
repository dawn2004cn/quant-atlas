"""Nested blueprint for wisdom mesh routes."""

from __future__ import annotations

from flask import Blueprint

wisdom_mesh_blueprint = Blueprint("wisdom_mesh", __name__, url_prefix="/wisdom-mesh")
