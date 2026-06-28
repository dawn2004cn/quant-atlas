from __future__ import annotations

"""兼容旧 import 路径；实现已迁至 ``app.agents.research``。"""


from .research import (
    RESEARCH_GRAPH_NODES,
    ResearchState,
    build_custom_trading_graph,
    package_full_report,
)
from .research.state import INVESTMENT_DEBATE_ROUNDS, RISK_DEBATE_ROUNDS

__all__ = [
    "INVESTMENT_DEBATE_ROUNDS",
    "RESEARCH_GRAPH_NODES",
    "RISK_DEBATE_ROUNDS",
    "ResearchState",
    "build_custom_trading_graph",
    "package_full_report",
]
