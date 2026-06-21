"""Legacy Route Compatibility Layer."""

from flask import Blueprint, redirect, url_for

legacy_bp = Blueprint("legacy_routes", __name__)

@legacy_bp.route("/api/v1/long-term-select", methods=["GET", "POST"])
def long_term_select_legacy():
    return redirect(url_for("quant_ai.long_term_select"), code=307)

@legacy_bp.route("/api/v1/experiments", methods=["GET"])
def experiments_legacy():
    return redirect(url_for("agent-swarm.list_experiments"), code=307)
