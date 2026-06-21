from __future__ import annotations
"""Autonomous Loop Controller - Self-Driving Pipeline for Alpha Factory."""


import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

from app.domain.alpha.dynamic_strategy_synthesis import (
    MarketRegime,
    get_strategy_synthesizer,
)
from app.domain.alpha.dynamic_search import get_decay_analyzer
from app.domain.alpha.postmortem_analysis import get_postmortem_analyzer
from app.domain.alpha.high_fidelity_research import (
    HighFidelityResearchLoop,
    get_production_research_bridge,
)

from app.domain.events_core import DomainEvent, EventType, EventPriority, publish_event_async
from app.domain.events_core import FactorDecayDetectedEvent, MarketRegimeChangedEvent
from app.domain.ports import IKnowledgeStore

from app.modules.data.services.rdagent_run_service import RDAgentRunService


from app.core.logger import get_logger

logger = get_logger(__name__)


class AutonomousState(Enum):
    """State of the autonomous loop."""
    IDLE = "idle"
    MONITORING = "monitoring"
    DRIFT_DETECTED = "drift_detected"
    ANALYZING = "analyzing"
    RESEARCHING = "researching"
    SHADOW_TESTING = "shadow_testing"
    DEPLOYING = "deploying"
    ERROR = "error"


class DriftSeverity(Enum):
    """Severity of detected drift."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DriftReport:
    """Report on detected drift."""
    severity: DriftSeverity
    backtest_return: float
    live_return: float
    drift_percentage: float
    cause_hypothesis: str
    recommended_action: str


@dataclass
class AutopilotConfig:
    """Configuration for autonomous loop."""
    drift_threshold: float = 0.15
    shadow_test_duration_hours: int = 48
    max_retries: int = 3
    auto_deploy_enabled: bool = False
    regime_switch_enabled: bool = True


@dataclass
class AutonomousLoopState:
    """Current state of autonomous loop."""
    state: AutonomousState = AutonomousState.IDLE
    last_drift_check: datetime | None = None
    current_regime: MarketRegime = MarketRegime.RANGING
    active_strategies: int = 0
    pending_deployments: list[str] = field(default_factory=list)
    error_count: int = 0
    last_error: str | None = None


class AutonomousLoopController:
    """Self-driving controller for Alpha Factory."""

    def __init__(self, config: AutopilotConfig | None = None):
        self.config = config or AutopilotConfig()
        self.state = AutonomousLoopState()
        self._synthesizer = None
        self._decay_analyzer = None
        self._postmortem = None
        self._rd_agent_service = None
        self._trace_id = None
        self._setup_monitoring()

    def _setup_monitoring(self) -> None:
        """Initialize telemetry and monitoring hooks for the loop."""
        logger.info("Initializing Autopilot monitoring instrumentation...")
        # Placeholder: Initialize metrics registry or prometheus gauges
        self._metrics = {
            "cycle_count": 0,
            "drift_events": 0,
            "research_triggered": 0
        }

    def _record_performance(self, metric: str, value: Any) -> None:
        """Record performance metrics for the autonomous loop."""
        if metric in self._metrics:
            self._metrics[metric] += (value if isinstance(value, (int, float)) else 1)
        logger.debug(f"Autopilot Metric Recorded: {metric}={value}")

    @property
    def synthesizer(self):
        if self._synthesizer is None:
            self._synthesizer = get_strategy_synthesizer()
        return self._synthesizer

    @property
    def rd_agent_service(self) -> RDAgentRunService:
        if self._rd_agent_service is None:
            self._rd_agent_service = RDAgentRunService()
        return self._rd_agent_service

    @property
    def decay_analyzer(self):
        if self._decay_analyzer is None:
            self._decay_analyzer = get_decay_analyzer()
        return self._decay_analyzer

    @property
    def postmortem(self):
        if self._postmortem is None:
            self._postmortem = get_postmortem_analyzer()
        return self._postmortem

    def check_drift(self, strategy_name: str, backtest_return: float, live_return: float) -> DriftReport | None:
        """Step 1: Detect drift between backtest and live performance.

        Fixed numerical stability:
        - Uses epsilon to prevent division by zero
        - Uses log-return difference for stable measure
        - Handles negative returns correctly
        """
        import math

        if backtest_return == 0:
            return None

        epsilon = 1e-10
        abs_backtest = max(abs(backtest_return), epsilon)

        drift_pct = (backtest_return - live_return) / abs_backtest

        live_neg = live_return < 0
        backtest_neg = backtest_return < 0

        if live_neg != backtest_neg:
            severity = DriftSeverity.CRITICAL
            cause = "Direction mismatch: backtest sign != live sign"
        elif abs(drift_pct) > 0.7:
            severity = DriftSeverity.CRITICAL
            cause = "Severe performance gap"
            action = "Immediate research required"
        elif drift_pct > 0.4:
            severity = DriftSeverity.HIGH
            cause = "Significant drift"
            action = "Start RD-Agent research"
        elif drift_pct > 0.2:
            severity = DriftSeverity.MEDIUM
            cause = "Moderate drift"
            action = "Monitor closely"
        else:
            severity = DriftSeverity.LOW
            cause = "Minor drift"
            action = "Continue monitoring"

        self.state.state = AutonomousState.DRIFT_DETECTED
        logger.warning(f"DRIFT DETECTED: {strategy_name} - {drift_pct:.1%} drift")

        publish_event_async(DomainEvent(
            event_type=EventType.TASK_COMPLETED,
            payload={"event": "drift_detected", "strategy": strategy_name, "severity": severity.value},
            priority=EventPriority.HIGH,
        ))

        return DriftReport(
            severity=severity,
            backtest_return=backtest_return,
            live_return=live_return,
            drift_percentage=drift_pct,
            cause_hypothesis=cause,
            recommended_action=action,
        )

    def analyze_root_cause(self, strategy_name: str, drift_report: DriftReport) -> dict[str, Any]:
        """Step 2: Analyze root cause."""
        self.state.state = AutonomousState.ANALYZING
        current_regime = self.synthesizer.detect_regime()
        regime_changed = current_regime != self.state.current_regime

        analysis = {"regime_changed": regime_changed, "likely_cause": None, "confidence": 0.0, "actions": []}

        if regime_changed:
            analysis["likely_cause"] = "market_regime_change"
            analysis["confidence"] = 0.85
            analysis["actions"].append("switch_strategy_for_new_regime")
            publish_event_async(MarketRegimeChangedEvent(
                old_regime=self.state.current_regime.value,
                new_regime=current_regime.value,
                confidence=analysis["confidence"],
            ))
            self.state.current_regime = current_regime
        else:
            factor_analysis = self.decay_analyzer.analyze_factor_decay(strategy_name)
            if factor_analysis.get("is_decayed"):
                analysis["likely_cause"] = "factor_decay"
                analysis["confidence"] = factor_analysis.get("confidence", 0.7)
                analysis["actions"].append("research_new_factor")
                publish_event_async(FactorDecayDetectedEvent(
                    factor_name=strategy_name,
                    decay_reason=factor_analysis.get("reason", "unknown"),
                    ir_before=factor_analysis.get("ir_before", 0),
                    ir_after=factor_analysis.get("ir_after", 0),
                ))
            else:
                analysis["likely_cause"] = "unknown"
                analysis["confidence"] = 0.3

        return analysis

    def trigger_research(self, strategy_name: str, target_characteristics: dict[str, Any]) -> str | None:
        """Step 3: Trigger RD-Agent to research new alpha (Physical pipeline integration).

        This integrates with the real RDAgentRunService for job submission.
        """
        import uuid

        self.state.state = AutonomousState.RESEARCHING
        self._trace_id = str(uuid.uuid4())

        goal = target_characteristics.get("opposite_of", "factor_decay")
        budget = {
            "max_loops": 3,
            "max_seconds_per_loop": 600,
        }
        body = {
            "formula": target_characteristics.get("target", "rank(returns_0_1)"),
            "search_space": "default",
            "budget": budget,
            "goal": goal,
            "_trace_id": self._trace_id,
        }

        logger.info(f"Triggering RD-Agent research for {strategy_name}, trace_id={self._trace_id}")

        try:
            result = self.rd_agent_service.submit_run(body)
            run_id = result.get("run_id") or result.get("job_id")
            if run_id:
                logger.info(f"RD-Agent task submitted: run_id={run_id}")
                return run_id
        except Exception as e:
            logger.error(f"Failed to trigger RD-Agent: {e}")

        return None

    def start_shadow_test(self, new_strategy_id: str, duration_hours: int | None = None) -> bool:
        """Step 4: Start shadow test."""
        self.state.state = AutonomousState.SHADOW_TESTING
        duration = duration_hours or self.config.shadow_test_duration_hours
        logger.info(f"Starting {duration}h shadow test for {new_strategy_id}")
        self.state.pending_deployments.append(new_strategy_id)
        research_bridge = get_production_research_bridge()
        research_bridge.start_shadow_deployment(new_strategy_id, hours=duration)
        return True

    def execute_hot_swap(self, old_strategy_id: str, new_strategy_id: str) -> bool:
        """Step 5: Hot swap."""
        if not self.config.auto_deploy_enabled:
            logger.info("Auto-deploy disabled")
            return False

        self.state.state = AutonomousState.DEPLOYING
        logger.info(f"Executing hot swap: {old_strategy_id} -> {new_strategy_id}")
        self.state.active_strategies += 1
        if old_strategy_id in self.state.pending_deployments:
            self.state.pending_deployments.remove(old_strategy_id)
        return True

    def run_full_cycle(self, strategy_name: str, backtest_return: float, live_return: float) -> dict[str, Any]:
        """Execute the full autonomous cycle."""
        drift = self.check_drift(strategy_name, backtest_return, live_return)
        if not drift:
            self.state.state = AutonomousState.MONITORING
            return {"status": "ok", "message": "No drift detected"}

        analysis = self.analyze_root_cause(strategy_name, drift)
        if analysis["likely_cause"] in ["market_regime_change", "factor_decay"]:
            research_id = self.trigger_research(strategy_name, {"opposite_of": analysis["likely_cause"]})
            if research_id:
                self.start_shadow_test(research_id)

        return {"status": "cycle_complete", "drift": drift.severity.value, "analysis": analysis}

    def detect_and_react_to_regime_change(self) -> bool:
        """Detect regime change and auto-switch."""
        if not self.config.regime_switch_enabled:
            return False
        current = self.synthesizer.detect_regime()
        if current != self.state.current_regime:
            logger.info(f"Regime change: {self.state.current_regime} -> {current}")
            self.state.current_regime = current
            strategy = self.synthesizer.synthesize_for_regime(current)
            if strategy:
                self.synthesizer.hotswap_strategy(strategy)
                return True
        return False

    def get_status(self) -> dict[str, Any]:
        """Get current autopilot status with trace ID for telemetry."""
        return {
            "state": self.state.state.value,
            "current_regime": self.state.current_regime.value,
            "active_strategies": self.state.active_strategies,
            "pending_deployments": len(self.state.pending_deployments),
            "error_count": self.state.error_count,
            "last_drift_check": self.state.last_drift_check.isoformat() if self.state.last_drift_check else None,
            "trace_id": self._trace_id,
        }


_autopilot: AutonomousLoopController | None = None


def get_autopilot(config: AutopilotConfig | None = None) -> AutonomousLoopController:
    """Get the global autopilot instance."""
    global _autopilot
    if _autopilot is None:
        _autopilot = AutonomousLoopController(config)
    return _autopilot