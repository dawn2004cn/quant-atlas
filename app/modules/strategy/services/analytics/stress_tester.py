from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class StressTestResult:
    scenario_id: str
    strategy_id: str
    max_drawdown: float
    long_risk: bool
    risk_metrics: dict[str, Any]
    timestamp: str


class StressTestService:
    def run_scenario(
        self,
        *,
        strategy: str,
        scenario: str,
        severity: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[StressTestResult]:
        severity_factor = {"low": 0.05, "medium": 0.12, "high": 0.25, "critical": 0.4}.get(str(severity).lower(), 0.12)
        return [
            StressTestResult(
                scenario_id=scenario,
                strategy_id=strategy,
                max_drawdown=severity_factor,
                long_risk=True,
                risk_metrics={"correlation": {}, "max_drawdown": severity_factor},
                timestamp=(start_date or datetime.now(timezone.utc)).isoformat(),
            )
        ]
