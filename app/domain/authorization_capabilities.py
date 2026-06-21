"""Capability vocabulary for authorization checks.

Capabilities are atomic permissions that can be granted to roles.
New capabilities must be added here to avoid stringly-typed drift.
"""
from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    AI_DIAGNOSIS = "ai_diagnosis"
    BACKTEST = "backtest"
    REALTIME_ALERT = "realtime_alert"
    QLIB = "qlib"
    PORTFOLIO_MANAGE = "portfolio_manage"
    SIGNAL_FLAG = "signal_flag"
    INVESTMENT_MANAGER = "investment_manager"
    RESEARCH_REPORT = "research_report"
    DATA_BACKFILL = "data_backfill"
    SYSTEM_CONFIG = "system_config"
    USER_MANAGE = "user_manage"
