"""Test data factories for domain entities.

Lightweight builder functions — no external dependencies (factory-boy, etc.).
Each function returns a fully-constructed domain object with sensible defaults.

Usage::

    from tests.factories.domain import build_user, build_stock_quote

    def test_user_can_login():
        user = build_user(password="secret123")
        assert user.check_password("secret123")
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_research_state(**overrides: Any) -> dict[str, Any]:
    """Build a minimal ResearchState dict for agent tests."""
    base: dict[str, Any] = {
        "ticker": "600519.SH",
        "user_id": 1,
        "query": "分析贵州茅台",
        "conversation_log": [],
        "supervisor_memo": "",
        "debate_turn": 0,
        "risk_debate_turn": 0,
        "investment_debate_state": {"bull_history": "", "bear_history": "", "history": ""},
        "risk_debate_state": {"risky_history": "", "safe_history": "", "history": ""},
        "macro_report": "",
        "fundamental_report": "",
        "technical_report": "",
        "sentiment_report": "",
        "backtest_report": "",
        "risk_manager_report": "",
        "fingpt_forecast": "",
        "decision_dashboard": "",
        "chart_vision_report": "",
        "chart_vision_signal": "neutral",
        "chart_vision_confidence": 0.0,
    }
    base.update(overrides)
    return base


def build_market_bar(**overrides: Any) -> dict[str, Any]:
    """Build a single market bar dict (OHLCV)."""
    base: dict[str, Any] = {
        "date": "2024-01-15",
        "open": 1800.0,
        "high": 1850.0,
        "low": 1790.0,
        "close": 1830.0,
        "volume": 50000,
        "amount": 915000000.0,
    }
    base.update(overrides)
    return base


def build_backtest_result(**overrides: Any) -> dict[str, Any]:
    """Build a minimal backtest result dict."""
    base: dict[str, Any] = {
        "total_return": 0.15,
        "annual_return": 0.12,
        "sharpe_ratio": 1.2,
        "max_drawdown": -0.08,
        "volatility": 0.18,
        "win_rate": 0.55,
        "total_trades": 42,
        "symbols": ["600519.SH"],
    }
    base.update(overrides)
    return base


def build_evidence(**overrides: Any) -> dict[str, Any]:
    """Build a minimal evidence dict for blackboard tests."""
    base: dict[str, Any] = {
        "agent_name": "macro_analyst",
        "key": "price_history",
        "value": "Sample evidence text",
        "evidence_type": "MACRO",
        "strength": "MODERATE",
        "timestamp": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


def build_trade_order(**overrides: Any) -> dict[str, Any]:
    """Build a minimal trade order dict."""
    base: dict[str, Any] = {
        "symbol": "600519.SH",
        "side": "buy",
        "quantity": 100,
        "price": 1800.0,
        "order_type": "limit",
        "status": "pending",
        "timestamp": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base
