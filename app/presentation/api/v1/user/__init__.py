"""User API routes.

Group of API endpoints related to user management.
"""

from .routes_v1_user_lifecycle import user_lifecycle_bp
from .routes_v1_user_profile import user_profile_bp
from .routes_v1_portfolio_users import portfolio_users_bp

__all__ = [
    "user_lifecycle_bp",
    "user_profile_bp",
    "portfolio_users_bp",
]