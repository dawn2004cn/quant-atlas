"""Smoke: custom TradingAgents graph compiles (no live LLM / tools)."""

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langgraph.checkpoint.memory import MemorySaver

from app.agents.custom_trading_workflow import build_custom_trading_graph


def test_custom_trading_graph_compiles():
    llm = FakeListChatModel(responses=["stub"] * 80)
    g = build_custom_trading_graph(llm, checkpointer=MemorySaver())
    assert g.get_graph().nodes
