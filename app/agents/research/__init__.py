"""
六分析师研究流水线（本仓库自有实现，**不依赖** ``TradingAgents-CN`` / ``tradingagents`` 包）。

- ``state``：LangGraph 状态与节点名常量
- ``react_loop``：ReAct 工具循环
- ``catalog``：平台策略 id 列表文案
- ``graph``：编译工作流
- ``report``：终态 → API dict
"""

from .graph import build_custom_trading_graph
from .report import package_full_report
from .state import RESEARCH_GRAPH_NODES, ResearchState

__all__ = [
    "RESEARCH_GRAPH_NODES",
    "ResearchState",
    "build_custom_trading_graph",
    "package_full_report",
]
