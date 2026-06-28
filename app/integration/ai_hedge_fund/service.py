from __future__ import annotations

"""Main integration service for AI Hedge Fund.

Orchestrates the flow:
1. Run AI-Hedge-Fund multi-agent analysis
2. Aggregate signals from different analyst styles
3. Validate through RD-Agent (factor generation + validation)
4. Validate through Qlib (backtest)
5. Present results for UI display
"""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger

from .adapters import (
    HedgeFundAgentAdapter,
    QlibValidationAdapter,
    RDAgentValidationAdapter,
)
from .dto import (
    AgentSignal,
    HedgeFundAnalysisRequest,
    HedgeFundAnalysisResult,
    ValidationResult,
)

logger = get_logger(__name__)


class AIHedgeFundIntegrationService:
    """Integration service that makes AI-Hedge-Fund the platform's intelligent research team.

    Flow:
    1. Analyze symbols using multi-agent AI-Hedge-Fund system
    2. Aggregate signals into investment thesis
    3. Validate through RD-Agent (strategy generation + backtest)
    4. Validate through Qlib (historical backtest)
    5. Return research report for UI display
    """

    def __init__(
        self,
        agent_adapter: HedgeFundAgentAdapter | None = None,
        rdagent_adapter: RDAgentValidationAdapter | None = None,
        qlib_adapter: QlibValidationAdapter | None = None,
        investment_committee_service: Any = None,
    ):
        self._agent_adapter = agent_adapter or HedgeFundAgentAdapter()
        self._rdagent_adapter = rdagent_adapter
        self._qlib_adapter = qlib_adapter
        self._investment_committee = investment_committee_service

    def analyze(
        self,
        request: HedgeFundAnalysisRequest,
        run_validation: bool = True,
    ) -> HedgeFundAnalysisResult:
        """Run complete analysis with optional validation."""

        logger.info(f"Starting AI-Hedge-Fund analysis for {request.symbols}")

        agent_results = self._agent_adapter.run_analysis(
            symbols=request.symbols,
            start_date=request.start_date,
            end_date=request.end_date,
            selected_agents=request.selected_agents,
        )

        all_signals = []
        for symbol_result in agent_results:
            symbol_result["symbol"]
            for agent in symbol_result["agents"]:
                all_signals.append(AgentSignal(
                    agent_name=agent["agent_name"],
                    agent_style=agent["agent_style"],
                    signal=agent["signal"],
                    confidence=agent["confidence"],
                    reasoning=agent["reasoning"],
                    analysis_details=agent.get("analysis_details", {}),
                ))

        aggregated_signal, consensus_score = self._aggregate_signals(all_signals)

        result = HedgeFundAnalysisResult(
            symbols=request.symbols,
            agent_signals=all_signals,
            aggregated_signal=aggregated_signal,
            consensus_score=consensus_score,
        )

        if run_validation and request.symbols:
            result = self._run_validation(result, request)

        result.summary = self._generate_summary(result)

        return result

    def _aggregate_signals(
        self,
        signals: list[AgentSignal],
    ) -> tuple[str, float]:
        """Aggregate signals from multiple agents into a consensus."""

        if not signals:
            return "neutral", 0.0

        bullish_count = sum(1 for s in signals if s.signal == "bullish")
        bearish_count = sum(1 for s in signals if s.signal == "bearish")
        sum(1 for s in signals if s.signal == "neutral")

        total = len(signals)
        consensus_score = (bullish_count - bearish_count) / total

        if consensus_score > 0.3:
            return "bullish", consensus_score
        elif consensus_score < -0.3:
            return "bearish", consensus_score
        elif consensus_score > 0:
            return "slightly_bullish", consensus_score
        elif consensus_score < 0:
            return "slightly_bearish", consensus_score
        else:
            return "neutral", 0.0

    def _run_validation(
        self,
        result: HedgeFundAnalysisResult,
        request: HedgeFundAnalysisRequest,
    ) -> HedgeFundAnalysisResult:
        """Run RD-Agent and Qlib validation."""

        primary_symbol = request.symbols[0] if request.symbols else ""

        if self._rdagent_adapter and primary_symbol:
            logger.info(f"Submitting to RD-Agent for validation: {primary_symbol}")

            rd_validation = self._rdagent_adapter.validate_signal(
                symbol=primary_symbol,
                signal=result.aggregated_signal,
                agent_signals=[
                    {
                        "agent_name": s.agent_name,
                        "signal": s.signal,
                        "reasoning": s.reasoning,
                    }
                    for s in result.agent_signals
                ],
            )

            result.validation_results.append(ValidationResult(
                validation_type="rd_agent",
                passed=rd_validation.get("passed", False),
                metrics=rd_validation.get("metrics", {}),
                errors=rd_validation.get("errors", []),
            ))

            if rd_validation.get("job_id"):
                result.rd_agent_job_id = rd_validation["job_id"]

        if self._qlib_adapter and primary_symbol:
            logger.info(f"Running Qlib validation for: {primary_symbol}")

            qlib_validation = self._qlib_adapter.validate_with_qlib(
                symbol=primary_symbol,
                signal=result.aggregated_signal,
                start_date=request.start_date,
                end_date=request.end_date,
            )

            result.validation_results.append(ValidationResult(
                validation_type="qlib",
                passed=qlib_validation.get("passed", False),
                backtest_result=qlib_validation.get("backtest_result"),
                errors=qlib_validation.get("errors", []),
            ))

            result.qlib_backtest_result = qlib_validation.get("backtest_result")

        validation_passed = all(v.passed for v in result.validation_results)
        result.validation_passed = validation_passed
        result.is_ready_for_trading = (
            validation_passed and
            result.consensus_score > 0.2 and
            result.aggregated_signal in ["bullish", "slightly_bullish"]
        )

        return result

    def _generate_summary(self, result: HedgeFundAnalysisResult) -> str:
        """Generate human-readable summary."""

        bullish = sum(1 for s in result.agent_signals if s.signal == "bullish")
        bearish = sum(1 for s in result.agent_signals if s.signal == "bearish")
        neutral = sum(1 for s in result.agent_signals if s.signal == "neutral")

        agent_styles = set(s.agent_style for s in result.agent_signals)

        summary = (
            f"AI Research Team analysis for {', '.join(result.symbols)}: "
            f"{bullish} bullish, {bearish} bearish, {neutral} neutral signals. "
            f"Consensus: {result.aggregated_signal.upper()} (score: {result.consensus_score:.2f}). "
            f"Analysis covers: {', '.join(agent_styles)}. "
        )

        if result.validation_passed:
            summary += "Signal validated by RD-Agent and Qlib backtest. Ready for consideration."
        elif result.validation_results:
            summary += f"Validation status: {sum(1 for v in result.validation_results if v.passed)}/{len(result.validation_results)} passed."
        else:
            summary += "Validation pending."

        return summary

    def get_research_report(self, symbol: str) -> dict[str, Any]:
        """Get research report for a specific symbol.

        This would typically fetch from a stored research report database.
        """
        return {
            "symbol": symbol,
            "generated_at": datetime.now().isoformat(),
            "status": "Report generation not yet implemented",
        }


def create_integration_service(
    llm_adapter: Any = None,
    data_provider: Any = None,
    rd_agent_service: Any = None,
    qlib_service: Any = None,
    market_provider: Any = None,
    investment_committee_service: Any = None,
) -> AIHedgeFundIntegrationService:
    """Factory function to create the integration service."""

    from .adapters import create_hedge_fund_adapters

    agent_adapter, rdagent_adapter, qlib_adapter = create_hedge_fund_adapters(
        llm_adapter=llm_adapter,
        data_provider=data_provider,
        rd_agent_service=rd_agent_service,
        qlib_service=qlib_service,
        market_provider=market_provider,
    )

    return AIHedgeFundIntegrationService(
        agent_adapter=agent_adapter,
        rdagent_adapter=rdagent_adapter,
        qlib_adapter=qlib_adapter,
        investment_committee_service=investment_committee_service,
    )
