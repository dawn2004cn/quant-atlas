"""Default capability-to-role mapping.

Free: base discovery + watchlist
Pro:  base + research + execution
Admin: all
"""
from __future__ import annotations

from app.domain.authorization_capabilities import Capability

FREE_CAPABILITIES: set[Capability] = {
    Capability.REALTIME_ALERT,
}

PRO_CAPABILITIES: set[Capability] = FREE_CAPABILITIES | {
    Capability.AI_DIAGNOSIS,
    Capability.BACKTEST,
    Capability.QLIB,
    Capability.PORTFOLIO_MANAGE,
    Capability.SIGNAL_FLAG,
    Capability.INVESTMENT_MANAGER,
    Capability.RESEARCH_REPORT,
}

ADMIN_CAPABILITIES: set[Capability] = PRO_CAPABILITIES | {
    Capability.DATA_BACKFILL,
    Capability.SYSTEM_CONFIG,
    Capability.USER_MANAGE,
}


def capabilities_for_role(role: str) -> set[Capability]:
    role = (role or "").lower()
    if role in ("admin", "administrator"):
        return set(ADMIN_CAPABILITIES)
    if role in ("pro", "vip", "premium"):
        return set(PRO_CAPABILITIES)
    return set(FREE_CAPABILITIES)
