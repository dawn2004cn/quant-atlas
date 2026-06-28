"""Page blueprint — routes delegated to domain sub-modules."""

from flask import Blueprint

from .pages_admin import register_pages as register_admin_pages
from .pages_ai import register_pages as register_ai_pages
from .pages_market import register_pages as register_market_pages
from .pages_spa import register_spa_pages
from .pages_stock import register_pages as register_stock_pages


def create_pages_blueprint():
    """Build page routes from domain sub-modules."""
    blueprint = Blueprint("pages", __name__)
    register_market_pages(blueprint)
    register_ai_pages(blueprint)
    register_stock_pages(blueprint)
    register_admin_pages(blueprint)
    register_spa_pages(blueprint)
    return blueprint
