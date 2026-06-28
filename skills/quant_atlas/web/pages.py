"""
Quant Atlas Skill - Web Pages
Auto-generated entry point for skill system.
"""

from flask import Blueprint

from .pages_admin import register_pages as register_admin_pages
from .pages_ai import register_pages as register_ai_pages
from .pages_market import register_pages as register_market_pages
from .pages_spa import register_spa_pages
from .pages_stock import register_pages as register_stock_pages


def register_pages(blueprint: Blueprint):
    """Register all Quant Atlas web pages."""
    register_market_pages(blueprint)
    register_ai_pages(blueprint)
    register_stock_pages(blueprint)
    register_admin_pages(blueprint)
    register_spa_pages(blueprint)
