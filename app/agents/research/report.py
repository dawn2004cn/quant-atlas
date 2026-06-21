from __future__ import annotations
"""将 LangGraph 终态整理为 API / 前端可用的 dict。"""


from typing import Any

from .catalog import strategy_catalog_text
from .state import (
    INVESTMENT_DEBATE_ROUNDS,
    RISK_DEBATE_ROUNDS,
    ResearchState,
)


def package_full_report(state: ResearchState) -> dict[str, Any]:
    iv = state.get("investment_debate_state") or {}
    rd = state.get("risk_debate_state") or {}
    analysts = {
        "macro": state.get("macro_report", ""),
        "fundamental": state.get("fundamental_report", ""),
        "technical": state.get("technical_report", ""),
        "sentiment": state.get("sentiment_report", ""),
        "backtest_optimizer": state.get("backtest_report", ""),
        "risk_manager": state.get("risk_manager_report", ""),
        "decision_dashboard": state.get("decision_dashboard", ""),
        "fingpt_forecast": state.get("fingpt_forecast", ""),
    }
    md_parts = [
        f"# 研究标的: {state.get('ticker', '')}",
        f"## 用户问题\n{state.get('query', '')}",
        analysts["decision_dashboard"],
        "## FinGPT 深度预测\n" + analysts["fingpt_forecast"],
        "## Supervisor\n" + str(state.get("supervisor_memo", "")),
        "## Macro Analyst\n" + analysts["macro"],
        "## Fundamental Analyst\n" + analysts["fundamental"],
        "## Technical Analyst\n" + analysts["technical"],
        "## Sentiment Analyst\n" + analysts["sentiment"],
        "## Backtest Optimizer\n" + analysts["backtest_optimizer"],
        "## Investment Debate (Bull / Bear)\n" + str(iv.get("history", "")),
        "## Risk Debate (Risk-Seeking / Risk-Averse)\n" + str(rd.get("history", "")),
        "## Risk Manager (Final)\n" + analysts["risk_manager"],
    ]
    return {
        "ok": True,
        "ticker": state.get("ticker"),
        "query": state.get("query"),
        "user_id": state.get("user_id"),
        "conversation_log": list(state.get("conversation_log") or []),
        "supervisor_memo": state.get("supervisor_memo"),
        "analyst_reports": analysts,
        "investment_debate": {
            "bull_history": iv.get("bull_history", ""),
            "bear_history": iv.get("bear_history", ""),
            "combined_history": iv.get("history", ""),
            "rounds": INVESTMENT_DEBATE_ROUNDS,
        },
        "risk_debate": {
            "risky_history": rd.get("risky_history", ""),
            "safe_history": rd.get("safe_history", ""),
            "combined_history": rd.get("history", ""),
            "rounds": RISK_DEBATE_ROUNDS,
        },
        "full_report_markdown": "\n\n".join(md_parts),
        "registered_strategies_used_hint": strategy_catalog_text(),
    }
