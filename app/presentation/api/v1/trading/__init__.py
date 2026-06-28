"""Trading API routes.

Group of API endpoints related to trading.
"""

from .routes_v1_portfolio import portfolio_bp
from .routes_v1_signal_flag import signal_flag_bp
from .routes_v1_trade_plan import trade_plan_bp

__all__ = [
    "portfolio_bp",
    "signal_flag_bp",
    "trade_plan_bp",
]
