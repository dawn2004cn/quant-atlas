from __future__ import annotations
"""Warren Buffett Agent - Oracle of Omaha.

Implements Buffett's value investing philosophy:
- Wide economic moat
- Financial fortress (high ROE, low debt)
- Intrinsic value > market price
- Durable competitive advantage
"""


import json
from typing import Any

from .base import AgentSignal, AgentAnalysisContext, AgentConfig, BaseHedgeFundAgent, SignalType
from ..adapters import get_llm


BUFFETT_SYSTEM_PROMPT = """You are Warren Buffett, the Oracle of Omaha, making investment decisions using Buffett's principles:

1. Seek companies with wide economic moats - brand power, network effects, cost advantages, regulatory moats, switching costs.
2. Financial fortress: consistently high ROE (>15%), low/no debt, strong free cash flow.
3. Intrinsic value > market price - margin of safety required.
4. Management with integrity and capital allocation skills.
5. Understandable business - you invest what you know.
6. Long-term holding (forever).

In your analysis:
- Focus on moat durability and competitive advantage.
- Analyze ROE, debt/equity, free cash flow trends.
- Calculate intrinsic value using DCF or multiples.
- Provide margin of safety assessment.
- Use a calm, patient, rational tone.

Return your final recommendation (bullish/bearish/neutral) with 0-100 confidence and thorough reasoning."""


class WarrenBuffettAgent(BaseHedgeFundAgent):
    """Warren Buffett style agent."""

    def __init__(self):
        config = AgentConfig(
            agent_id="warren_buffett",
            system_prompt=BUFFETT_SYSTEM_PROMPT,
        )
        super().__init__(config)

    def analyze(self, context: AgentAnalysisContext) -> AgentSignal:
        """Run Buffett analysis."""
        llm = get_llm()
        prompt = self._build_prompt(context)
        response = llm.invoke(prompt)
        return self._parse_response(response)

    def _build_prompt(self, context: AgentAnalysisContext) -> str:
        """Build analysis prompt."""
        data_summary = self._summarize_data(context)
        return f"""Based on the following financial data for {context.symbol} ({context.market}):

{data_summary}

Using Warren Buffett's investing principles, analyze and provide:
1. Signal: bullish, bearish, or neutral
2. Confidence: 0-100
3. Reasoning: Your analysis focusing on moat, ROE, intrinsic value, margin of safety
"""

    def _summarize_data(self, context: AgentAnalysisContext) -> str:
        """Summarize financial data."""
        lines = [f"Symbol: {context.symbol}", f"Market: {context.market}"]

        if context.financial_metrics:
            latest = context.financial_metrics[0]
            lines.append(f"ROE: {latest.get('return_on_equity', 'N/A')}")
            lines.append(f"Debt/Equity: {latest.get('debt_to_equity', 'N/A')}")
            lines.append(f"Free Cash Flow: {latest.get('free_cash_flow', 'N/A')}")

        if context.market_cap:
            lines.append(f"Market Cap: ${context.market_cap:,.0f}")

        return "\n".join(lines)

    def _parse_response(self, response: Any) -> AgentSignal:
        """Parse LLM response to AgentSignal."""
        content = response.content if hasattr(response, "content") else str(response)
        return AgentSignal(
            agent_id="warren_buffett",
            agent_name="Warren Buffett",
            style="Value Investing",
            signal="neutral",
            confidence=50,
            reasoning=content[:500],
        )


def create_warren_buffett_agent() -> WarrenBuffettAgent:
    """Factory function."""
    return WarrenBuffettAgent()


__all__ = ["WarrenBuffettAgent", "create_warren_buffett_agent"]