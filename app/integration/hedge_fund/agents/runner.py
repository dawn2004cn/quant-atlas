from __future__ import annotations

"""Hedge Fund Agents - Factory and Runner.

This module provides:
- get_llm(): Get LLM instance configured in quant-atlas
- run_agent(): Run a single agent
- run_agents(): Run multiple agents in parallel
- get_agent_registry(): Get all available agent classes

Now with Openclaw personality enhancement!
"""


from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.core.llm_config import get_llm as _get_llm
from app.core.logger import get_logger

from .base import AgentAnalysisContext, AgentSignal
from .openclaw import get_communication_style, get_enhanced_system_prompt

logger = get_logger(__name__)


def get_llm() -> Any:
    """Get LLM instance from quant-atlas config."""
    try:
        return _get_llm()
    except Exception as e:
        logger.warning(f"LLM not configured, returning None: {e}")
        return None


def run_agent(
    agent_id: str,
    context: AgentAnalysisContext,
    llm: Any = None,
) -> AgentSignal:
    """Run a single hedge fund agent.

    Args:
        agent_id: The agent ID (e.g., 'warren_buffett', 'bill_ackman')
        context: Analysis context with symbol, market, financial data
        llm: Optional LLM instance (will get from config if not provided)

    Returns:
        AgentSignal with the agent's analysis
    """
    if llm is None:
        llm = get_llm()

    if llm is None:
        return _create_fallback_signal(agent_id, "LLM not available")

    try:
        return _run_llm_agent(agent_id, context, llm)
    except Exception as e:
        logger.error(f"Error running agent {agent_id}: {e}")
        return _create_fallback_signal(agent_id, str(e))


def _run_llm_agent(
    agent_id: str,
    context: AgentAnalysisContext,
    llm: Any,
) -> AgentSignal:
    """Run agent with LLM and enhanced prompts."""

    base_prompt = _get_system_prompt(agent_id)
    enhanced_prompt = get_enhanced_system_prompt(agent_id, base_prompt)
    user_prompt = _build_user_prompt(agent_id, context)

    style = get_communication_style(agent_id)

    response = llm.invoke([
        {"role": "system", "content": enhanced_prompt},
        {"role": "user", "content": user_prompt},
    ])

    content = response.content if hasattr(response, "content") else str(response)
    signal, confidence, reasoning = _parse_signal_output(content)

    return AgentSignal(
        agent_id=agent_id,
        agent_name=_get_agent_name(agent_id),
        style=style.get("style", _get_agent_style(agent_id)),
        signal=signal,
        confidence=confidence,
        reasoning=reasoning[:1000],
    )


def _get_system_prompt(agent_id: str) -> str:
    """Get system prompt for agent."""
    prompts = {
        "warren_buffett": """You are Warren Buffett, Oracle of Omaha.
- Seek wide economic moats, financial fortress, intrinsic value.
- Focus on ROE >15%, low debt, strong FCF.
- Margin of safety required.
- Long-term holding. Return bullish/bearish/neutral with confidence.""",

        "charlie_munger": """You are Charlie Munger, Buffett's partner.
- Excellent businesses at fair prices.
- Focus on management quality, predictability.
- Inversions thinking. Return bullish/bearish/neutral.""",

        "ben_graham": """You are Ben Graham, father of value investing.
- Net-net strategy, margin of safety.
- Focus on NCAV, Graham number.
- Deep value, undervaluing. Return bullish/bearish/neutral.""",

        "bill_ackman": """You are Bill Ackman, activist investor.
- High-conviction, brand moats, FCF.
- Activism potential, management changes.
- Concentrated bets. Return bullish/bearish/neutral.""",

        "cathie_wood": """You are Cathie Wood, ARK Invest.
- Disruptive innovation, exponential tech.
- Big ideas, high growth potential.
- Innovation period. Return bullish/bearish/neutral.""",

        "michael_burry": """You are Michael Burry, The Big Short.
- Contrarian deep value.
- Hidden assets, restructuring.
- High conviction short or long. Return bullish/bearish/neutral.""",

        "peter_lynch": """You are Peter Lynch, legendary manager.
- Invest what you know, 10-baggers.
- Lifestyle investing, growth at reasonable price.
- Technicals + fundamentals. Return bullish/bearish/neutral.""",

        "phil_fisher": """You are Phil Fisher, growth stock pioneer.
- Scuttlebutt method, 15 points.
- Growth at reasonable price.
- Management quality. Return bullish/bearish/neutral.""",

        "stanley_druckenmiller": """You are Stanley Druckenmiller, macro legend.
- Asymmetric risk-reward.
- Big bets when odds favor.
- Macro + momentum. Return bullish/bearish/neutral.""",

        "mohnish_pabrai": """You are Mohnish Pabrai, Dhandho investor.
- Low-risk high-reward, clones.
- High expectations + low price.
- Dhandho principles. Return bullish/bearish/neutral.""",

        "nassim_taleb": """You are Nassim Taleb, antifragility author.
- Tail risk, convexity.
- Black swan hedging.
- Antifragile positions. Return bullish/bearish/neutral.""",

        "aswath_damodaran": """You are Aswath Damodaran, valuation guru.
- DCF, multiples, options.
- Rigorous financial modeling.
- Fair value calculation. Return bullish/bearish/neutral.""",

        "valuation": """You are Valuation Agent.
- Calculate intrinsic value.
- DCF, multiples comparison.
- Return valuation signal.""",

        "fundamentals": """You are Fundamentals Agent.
- ROE, growth, profitability.
- Financial metrics analysis.
- Return fundamental signal.""",

        "technicals": """You are Technicals Agent.
- Price action, momentum.
- Chart patterns, indicators.
- Return technical signal.""",

        "sentiment": """You are Sentiment Agent.
- News flow, social sentiment.
- Crowd behavior.
- Return sentiment signal.""",

        "risk_manager": """You are Risk Manager.
- Volatility, drawdown risk.
- Position sizing, limits.
- Return risk-adjusted signal.""",

        "portfolio_manager": """You are Portfolio Manager.
- Aggregate all signals.
- Allocate weights.
- Return final decision.""",
    }
    return prompts.get(agent_id, "You are an investment analyst. Return bullish/bearish/neutral with confidence.")


def _get_agent_name(agent_id: str) -> str:
    """Get agent display name."""
    names = {
        "warren_buffett": "Warren Buffett",
        "charlie_munger": "Charlie Munger",
        "ben_graham": "Ben Graham",
        "bill_ackman": "Bill Ackman",
        "cathie_wood": "Cathie Wood",
        "michael_burry": "Michael Burry",
        "peter_lynch": "Peter Lynch",
        "phil_fisher": "Phil Fisher",
        "stanley_druckenmiller": "Stanley Druckenmiller",
        "mohnish_pabrai": "Mohnish Pabrai",
        "nassim_taleb": "Nassim Taleb",
        "aswath_damodaran": "Aswath Damodaran",
        "valuation": "Valuation Agent",
        "fundamentals": "Fundamentals Agent",
        "technicals": "Technicals Agent",
        "sentiment": "Sentiment Agent",
        "risk_manager": "Risk Manager",
        "portfolio_manager": "Portfolio Manager",
    }
    return names.get(agent_id, agent_id)


def _get_agent_style(agent_id: str) -> str:
    """Get agent style."""
    styles = {
        "warren_buffett": "Value Investing",
        "charlie_munger": "Business Quality",
        "ben_graham": "Deep Value",
        "bill_ackman": "Activist Investing",
        "cathie_wood": "Innovation/Growth",
        "michael_burry": "Contrarian/Deep Value",
        "peter_lynch": "Growth Investing",
        "phil_fisher": "Growth Stocks",
        "stanley_druckenmiller": "Macro/Momentum",
        "mohnish_pabrai": "GARP",
        "nassim_taleb": "Risk/Antifragility",
        "aswath_damodaran": "Valuation",
        "valuation": "Valuation",
        "fundamentals": "Fundamentals",
        "technicals": "Technical Analysis",
        "sentiment": "Sentiment Analysis",
        "risk_manager": "Risk Management",
        "portfolio_manager": "Portfolio Construction",
    }
    return styles.get(agent_id, "Analysis")


def _build_user_prompt(agent_id: str, context: AgentAnalysisContext) -> str:
    """Build user prompt with context data."""
    lines = [f"Analyze {context.symbol} ({context.market})", f"Period: {context.start_date} to {context.end_date}"]

    if context.financial_metrics:
        latest = context.financial_metrics[0]
        lines.append(f"ROE: {latest.get('return_on_equity')}")
        lines.append(f"Debt/Equity: {latest.get('debt_to_equity')}")
        lines.append(f"Free Cash Flow: {latest.get('free_cash_flow')}")
        lines.append(f"Revenue Growth: {latest.get('revenue_growth')}")

    if context.market_cap:
        lines.append(f"Market Cap: ${context.market_cap:,.0f}")

    if context.prices:
        if len(context.prices) > 0:
            latest_price = context.prices[0]
            lines.append(f"Latest Price: ${latest_price.get('close')}")

    return "\n".join(lines) + "\n\nProvide signal (bullish/bearish/neutral), confidence (0-100), reasoning."


def _parse_signal_output(content: str) -> tuple[str, float, str]:
    """Parse LLM output to signal components."""
    content_lower = content.lower()

    if "bullish" in content_lower and content_lower.find("bullish") < content_lower.find("bearish"):
        signal = "bullish"
    elif "bearish" in content_lower:
        signal = "bearish"
    else:
        signal = "neutral"

    import re
    confidence_match = re.search(r"confidence[:\s]+(\d+)", content_lower)
    if confidence_match:
        confidence = float(confidence_match.group(1))
    else:
        confidence = 50.0

    return signal, min(100, max(0, confidence)), content


def _create_fallback_signal(agent_id: str, error: str) -> AgentSignal:
    """Create fallback signal on error."""
    return AgentSignal(
        agent_id=agent_id,
        agent_name=_get_agent_name(agent_id),
        style=_get_agent_style(agent_id),
        signal="neutral",
        confidence=0,
        reasoning=f"Error: {error}",
    )


def run_agents(
    agent_ids: list[str],
    context: AgentAnalysisContext,
    max_workers: int = 6,
) -> list[AgentSignal]:
    """Run multiple agents in parallel.

    Args:
        agent_ids: List of agent IDs to run
        context: Analysis context
        max_workers: Max parallel workers

    Returns:
        List of AgentSignal from each agent
    """
    llm = get_llm()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_agent, agent_id, context, llm): agent_id
            for agent_id in agent_ids
        }

    results = []
    for future in futures:
        try:
            result = future.result(timeout=120)
            results.append(result)
        except Exception as e:
            agent_id = futures[future]
            logger.error(f"Agent {agent_id} failed: {e}")
            results.append(_create_fallback_signal(agent_id, str(e)))

    return results


def get_agent_registry() -> dict[str, Callable]:
    """Get registry of all available agent factories."""
    return {
        "warren_buffett": lambda: WarrenBuffettAgent(),
        "charlie_munger": lambda: CharlieMungerAgent(),
        "ben_graham": lambda: BenGrahamAgent(),
        "bill_ackman": lambda: BillAckmanAgent(),
        "cathie_wood": lambda: CathieWoodAgent(),
        "michael_burry": lambda: MichaelBurryAgent(),
        "peter_lynch": lambda: PeterLynchAgent(),
        "phil_fisher": lambda: PhilFisherAgent(),
        "stanley_druckenmiller": lambda: StanleyDruckenmillerAgent(),
        "mohnish_pabrai": lambda: MohnishPabraiAgent(),
        "nassim_taleb": lambda: NassimTalebAgent(),
        "aswath_damodaran": lambda: AswathDamodaranAgent(),
    }


# Lazy imports for agent factories
def WarrenBuffettAgent():
    from .warren_buffett import create_warren_buffett_agent
    return create_warren_buffett_agent()

def CharlieMungerAgent():
    return _create_generic_agent("charlie_munger")

def BenGrahamAgent():
    return _create_generic_agent("ben_graham")

def BillAckmanAgent():
    return _create_generic_agent("bill_ackman")

def CathieWoodAgent():
    return _create_generic_agent("cathie_wood")

def MichaelBurryAgent():
    return _create_generic_agent("michael_burry")

def PeterLynchAgent():
    return _create_generic_agent("peter_lynch")

def PhilFisherAgent():
    return _create_generic_agent("phil_fisher")

def StanleyDruckenmillerAgent():
    return _create_generic_agent("stanley_druckenmiller")

def MohnishPabraiAgent():
    return _create_generic_agent("mohnish_pabrai")

def NassimTalebAgent():
    return _create_generic_agent("nassim_taleb")

def AswathDamodaranAgent():
    return _create_generic_agent("aswath_damodaran")

def _create_generic_agent(agent_id: str):
    """Create generic agent."""
    from .base import AgentConfig, BaseHedgeFundAgent

    class GenericAgent(BaseHedgeFundAgent):
        def __init__(self):
            super().__init__(AgentConfig(
                agent_id=agent_id,
                system_prompt=_get_system_prompt(agent_id),
            ))

        def analyze(self, context: AgentAnalysisContext) -> AgentSignal:
            return run_agent(self.agent_id, context)

    return GenericAgent()


__all__ = [
    "get_llm",
    "run_agent",
    "run_agents",
    "get_agent_registry",
]
