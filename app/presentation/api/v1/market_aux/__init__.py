"""Market auxiliary API sub-package."""

from app.presentation.api.v1.market_aux.feed_routes import register_market_aux_feed_routes
from app.presentation.api.v1.market_aux.pulse_routes import register_market_aux_pulse_routes
from app.presentation.api.v1.market_aux.refresh_routes import register_market_aux_refresh_routes
from app.presentation.api.v1.market_aux.runtime import MarketAuxRuntime

__all__ = [
    "MarketAuxRuntime",
    "register_market_aux_feed_routes",
    "register_market_aux_pulse_routes",
    "register_market_aux_refresh_routes",
]
