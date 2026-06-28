"""Phase 18 Truth Droplet — renders the data hygiene dashboard."""

from __future__ import annotations

from flask import Blueprint, render_template

from app.core.logger import get_logger

logger = get_logger(__name__)

bp = Blueprint("truth_droplet", __name__)


@bp.route("/truth-droplet", methods=["GET"])
def truth_droplet_page():
    """Render the Truth Droplet dashboard page."""
    return render_template("truth_droplet.html")
