from __future__ import annotations

from flask import Blueprint

from ...core.registry import register_routes


@register_routes(name="stock", context="market_data", description="Stock route compatibility shim")
def register_stock_routes(blueprint: Blueprint, ctx) -> None:
    """Keep legacy dispatcher import but avoid double-registering stock submodules."""
    return None
