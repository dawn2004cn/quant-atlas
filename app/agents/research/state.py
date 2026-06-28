from __future__ import annotations

"""多智能体研究图状态：六分析师 + 辩论 + Risk Manager（本仓库自有实现）。"""


from typing_extensions import NotRequired, TypedDict

INVESTMENT_DEBATE_ROUNDS = 3
RISK_DEBATE_ROUNDS = 3


class InvestmentDebateState(TypedDict, total=False):
    bull_history: str
    bear_history: str
    history: str


class RiskDebateState(TypedDict, total=False):
    risky_history: str
    safe_history: str
    history: str


class ResearchState(TypedDict, total=False):
    ticker: str
    query: str
    user_id: int
    conversation_log: NotRequired[list[str]]
    supervisor_memo: str
    macro_report: str
    fundamental_report: str
    technical_report: str
    sentiment_report: str
    backtest_report: str
    debate_turn: NotRequired[int]
    investment_debate_state: NotRequired[InvestmentDebateState]
    risk_debate_turn: NotRequired[int]
    risk_debate_state: NotRequired[RiskDebateState]
    risk_manager_report: str
    decision_dashboard: str
    fingpt_forecast: str
    chart_vision_report: str
    chart_vision_signal: str
    chart_vision_confidence: float
    chart_vision_patterns: NotRequired[list[str]]


def merge_investment_history(state: InvestmentDebateState, key: str, chunk: str) -> InvestmentDebateState:
    out = dict(state)
    prev = str(out.get(key, ""))
    out[key] = (prev + "\n\n" + chunk).strip()
    out["history"] = (str(out.get("history", "")) + "\n\n" + chunk).strip()
    return out


def merge_risk_history(state: RiskDebateState, key: str, chunk: str) -> RiskDebateState:
    out = dict(state)
    prev = str(out.get(key, ""))
    out[key] = (prev + "\n\n" + chunk).strip()
    out["history"] = (str(out.get("history", "")) + "\n\n" + chunk).strip()
    return out


# 图节点名 — 与 ``config/research_graph_topology.json`` 同步（见 TopologyLoader）
def _default_graph_nodes() -> tuple[str, ...]:
    try:
        from app.agents.research.topology_loader import get_research_graph_node_ids

        return get_research_graph_node_ids()
    except Exception:
        return (
            "supervisor",
            "macro_analyst",
            "fundamental_analyst",
            "write_fundamental_evidence",
            "technical_analyst",
            "sentiment_analyst",
            "backtest_optimizer",
            "bull",
            "bear",
            "risky_analyst",
            "safe_analyst",
            "risk_manager",
            "fingpt_forecaster",
            "decision_dashboard",
        )


RESEARCH_GRAPH_NODES: tuple[str, ...] = _default_graph_nodes()
