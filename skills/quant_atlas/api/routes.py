"""
Quant Atlas Skill - API Routes
This skill provides the core quant-atlas API via the existing bootstrap.
"""

import logging

from flask import Blueprint

logger = logging.getLogger(__name__)


def register_routes(blueprint: Blueprint):
    """Register Quant Atlas API routes."""
    @blueprint.route("/health")
    def skill_health():
        return {"status": "ok", "skill": "quant_atlas"}
