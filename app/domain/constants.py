"""Named constants for the domain layer.

Eliminates magic numbers and strings scattered across application and
infrastructure code.  New code should import from this module instead of
hardcoding literals.

**Not** for configuration values (those belong in ``app.config.settings``).
These are stable business-domain constants that rarely change at runtime.
"""

from __future__ import annotations

# ── Time constants (seconds) ────────────────────────────────────────────

ONE_HOUR_SECONDS: int = 3600
ONE_DAY_SECONDS: int = 86_400
CACHE_TTL_DEFAULT: int = ONE_HOUR_SECONDS

# ── Risk / trading thresholds ──────────────────────────────────────────

DEFAULT_DAILY_LOSS_LIMIT: float = 0.05
DEFAULT_MAX_POSITION_PCT: float = 0.05
DEFAULT_STOP_LOSS_PCT: float = -0.05
DEFAULT_PARTICIPATION_LIMIT: float = 0.05
DEFAULT_LEARNING_RATE: float = 0.05
DEFAULT_IC_WARN_THRESHOLD: float = 0.05

# ── Market defaults ────────────────────────────────────────────────────

DEFAULT_MARKET_CODE: str = "CN"
CN_LOT_SIZE: int = 100

# ── Pagination defaults ────────────────────────────────────────────────

DEFAULT_LIST_LIMIT: int = 100
MAX_LIST_LIMIT: int = 500

# ── Trading calendar ───────────────────────────────────────────────────

TRADING_DAYS_PER_YEAR: int = 252

# ── Query defaults ─────────────────────────────────────────────────────

DEFAULT_HISTORY_LIMIT: int = 1000
DEFAULT_CHART_DAYS: int = 120
