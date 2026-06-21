"""Data Provenance Explorer (dispatcher)."""

from __future__ import annotations

from flask import Blueprint

from app.core.registry import register_routes
from app.presentation.api.v1.provenance import (
    register_provenance_dashboard_routes,
    register_provenance_fingerprint_routes,
)
from app.presentation.api.v1_context import ApiV1Context


@register_routes(name="provenance_explorer", context="system", description="Data provenance explorer")
def register_provenance_routes(parent: Blueprint, ctx: ApiV1Context) -> None:
    provenance_bp = Blueprint("provenance_explorer", __name__, url_prefix="/provenance")
    register_provenance_fingerprint_routes(provenance_bp, ctx)
    register_provenance_dashboard_routes(provenance_bp, ctx)
    parent.register_blueprint(provenance_bp)


# Backward compat for smoke tests
blueprint = Blueprint("provenance_explorer", __name__, url_prefix="/provenance")
