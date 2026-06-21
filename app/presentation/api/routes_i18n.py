"""API i18n routes."""

from flask import Blueprint, jsonify, request, session

from app.application.errors import ValidationError
from app.core.i18n import get_all_translations, get_i18n
from .common import ok_response

bp = Blueprint("i18n", __name__, url_prefix="/api/i18n")


@bp.route("", methods=["GET"])
@bp.route("/", methods=["GET"])
def handle_get_i18n():
    """Get translations for current locale."""
    return jsonify(get_all_translations())


@bp.route("/<locale>", methods=["GET"])
def get_i18n_locale(locale: str):
    """Get translations for specific locale."""
    i18n = get_i18n(locale)
    return jsonify(i18n.all())


@bp.route("/set_locale", methods=["POST"])
def set_locale():
    """Set locale for session."""
    data = request.get_json() or {}
    locale = data.get("locale", "zh")
    
    if locale not in ("zh", "en"):
        raise ValidationError("invalid_locale", details={"allowed": ["zh", "en"]})
    
    session["locale"] = locale
    return ok_response(data={"locale": locale})