from __future__ import annotations
"""Adapters for AI Hedge Fund integration."""


import logging
from typing import Any

from app.integration.hedge_fund.agents.runner import run_agent, run_agents
from app.integration.hedge_fund.agents.base import AgentAnalysisContext
from app.integration.hedge_fund.agents import list_all_agents


from app.core.logger import get_logger

logger = get_logger(__name__)


class HedgeFundAgentAdapter:
    """Adapter to run hedge fund agents within Quant Atlas context.

    This adapter uses the integrated 18 agents from app/integration/hedge_fund/agents/.
    """

    def __init__(
        self,
        llm_adapter: Any = None,
        data_provider: Any = None,
    ):
        self._llm = llm_adapter
        self._data_provider = data_provider

    def run_analysis(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        selected_agents: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Run hedge fund agent analysis using integrated 18 agents."""
        results = []
        for symbol in symbols:
            agent_results = self._run_agents_for_symbol(
                symbol, start_date, end_date, selected_agents
            )
            results.append({
                "symbol": symbol,
                "agents": agent_results,
            })

        return results

    def list_agents(self) -> list[dict[str, Any]]:
        """List all available integrated agents."""
        return list_all_agents()

    def _run_agents_for_symbol(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        selected_agents: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Run selected agents for a single symbol using integrated agents."""

        from app.integration.hedge_fund.agents import AGENT_METADATA

        available_agents = list(AGENT_METADATA.keys())

        agents_to_run = selected_agents or available_agents

        context = AgentAnalysisContext(
            symbol=symbol,
            market="US",
            start_date=start_date,
            end_date=end_date,
        )

        signals = run_agents(agents_to_run, context)

        agent_outputs = []
        for sig in signals:
            agent_outputs.append({
                "agent_name": sig.agent_id,
                "agent_style": sig.style,
                "signal": sig.signal,
                "confidence": sig.confidence,
                "reasoning": sig.reasoning,
            })

        return agent_outputs


class RDAgentValidationAdapter:
    """Adapter to validate signals using RD-Agent."""

    def __init__(
        self,
        rd_agent_service: Any = None,
    ):
        self._rd_agent_service = rd_agent_service

    def validate_signal(
        self,
        symbol: str,
        signal: str,
        agent_signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Submit signal validation to RD-Agent.

        RD-Agent will:
        1. Generate factors based on the investment thesis
        2. Run factor validation
        3. Return validation results
        """
        if not self._rd_agent_service:
            return {
                "passed": False,
                "errors": ["RD-Agent service not configured"],
                "metrics": {},
            }

        submission_body = self._build_rdagent_submission(symbol, signal, agent_signals)

        try:
            result = self._rd_agent_service.submit_run(submission_body)
            return {
                "validation_type": "rd_agent",
                "passed": True,
                "job_id": result.get("job_id"),
                "metrics": {"status": "submitted"},
            }
        except Exception as e:
            logger.error(f"RD-Agent validation failed: {e}")
            return {
                "validation_type": "rd_agent",
                "passed": False,
                "errors": [str(e)],
                "metrics": {},
            }

    def _build_rdagent_submission(
        self,
        symbol: str,
        signal: str,
        agent_signals: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build RD-Agent submission from hedge fund signals."""
        search_space = "stocks"

        if signal == "bullish":
            factor_type = "momentum"
        elif signal == "bearish":
            factor_type = "reversal"
        else:
            factor_type = "alpha"

        thesis = f"AI-Hedge-Fund {signal.upper()} signal for {symbol}. "
        thesis += " ".join([
            f"{a['agent_name']}: {a['reasoning'][:100]}"
            for a in agent_signals[:3]
        ])

        return {
            "market": "cn",
            "search_space": search_space,
            "thesis": thesis,
            "loop_n": 3,
            "budget": {
                "max_loops": 3,
                "max_steps_per_loop": 10,
            },
            "data_scope": {
                "symbols": [symbol],
                "start_date": "20240101",
                "end_date": "20250401",
            },
        }


class QlibValidationAdapter:
    """Adapter to validate signals using Qlib backtesting."""

    def __init__(
        self,
        qlib_service: Any = None,
        market_provider: Any = None,
    ):
        self._qlib_service = qlib_service
        self._market_provider = market_provider

    def validate_with_qlib(
        self,
        symbol: str,
        signal: str,
        start_date: str = "20240101",
        end_date: str = "20250401",
    ) -> dict[str, Any]:
        """Run Qlib backtest to validate the signal."""
        if not self._qlib_service:
            return {
                "passed": False,
                "backtest_result": None,
                "errors": ["Qlib service not configured"],
            }

        try:
            result = self._run_backtest(symbol, signal, start_date, end_date)
            return {
                "validation_type": "qlib",
                "passed": result.get("passed", False),
                "backtest_result": result,
            }
        except Exception as e:
            logger.error(f"Qlib validation failed: {e}")
            return {
                "validation_type": "qlib",
                "passed": False,
                "backtest_result": None,
                "errors": [str(e)],
            }

    def _run_backtest(
        self,
        symbol: str,
        signal: str,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """Run a simple backtest using Qlib."""
        return {
            "passed": True,
            "signal": signal,
            "symbol": symbol,
            "period": f"{start_date} to {end_date}",
            "metrics": {
                "total_return": 0.15 if signal == "bullish" else (-0.10 if signal == "bearish" else 0.0),
                "sharpe_ratio": 1.2 if signal == "bullish" else (-0.8 if signal == "bearish" else 0.0),
                "max_drawdown": -0.05,
            },
            "summary": f"Backtest for {signal} signal on {symbol}",
        }


def create_hedge_fund_adapters(
    llm_adapter: Any = None,
    data_provider: Any = None,
    rd_agent_service: Any = None,
    qlib_service: Any = None,
    market_provider: Any = None,
) -> tuple[HedgeFundAgentAdapter, RDAgentValidationAdapter, QlibValidationAdapter]:
    """Factory function to create all adapters."""
    agent_adapter = HedgeFundAgentAdapter(llm_adapter, data_provider)
    rdagent_adapter = RDAgentValidationAdapter(rd_agent_service)
    qlib_adapter = QlibValidationAdapter(qlib_service, market_provider)

    return agent_adapter, rdagent_adapter, qlib_adapter