from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Risk application service with domain model integration."""


from typing import Any
from uuid import uuid4

from app.application.dto.complete_dto import (
    PositionRiskDTO,
    RiskAlertDTO,
    RiskAssessmentDTO,
    RiskLimitDTO,
)
from app.application.events.event_bus import EventBus, EventType, publish_event
from app.core.logger import get_logger
from app.domain.models.risk_models import (
    RiskCalculator,
    RiskLevel,
)
from app.modules.portfolio_risk.services.entangled_risk_monitor import EntangledRiskMonitor

logger = get_logger(__name__)


class RiskApplicationService:
    """Application service for risk management using domain models."""

    def __init__(self, event_bus: EventBus | None = None):
        self._event_bus = event_bus or EventBus()
        self._entangled_risk_monitor = EntangledRiskMonitor(
            max_correlation=self._default_limit("max_correlation"),
            joint_budget=self._default_limit("max_position_size"),
        )
        self._risk_limits = {
            "max_position_size": 0.2,
            "max_sector_exposure": 0.4,
            "max_daily_loss": 0.05,
            "max_portfolio_leverage": 1.0,
            "max_correlation": 0.7,
        }
        self._alerts: list[RiskAlertDTO] = []
        logger.info("RiskApplicationService initialized")

    def _default_limit(self, name: str) -> float:
        defaults = {
            "max_position_size": 0.2,
            "max_sector_exposure": 0.4,
            "max_daily_loss": 0.05,
            "max_portfolio_leverage": 1.0,
            "max_correlation": 0.7,
        }
        return defaults.get(name, 0.0)

    async def assess_position_risk(
        self,
        code: str,
        name: str,
        quantity: int,
        price: float,
        total_portfolio_value: float,
        sector: str = "default",
    ) -> PositionRiskDTO:
        """Assess risk for a single position."""
        position_value = quantity * price
        weight = position_value / total_portfolio_value if total_portfolio_value > 0 else 0

        risk_metrics = RiskCalculator.calculate_position_risk(
            position_value=position_value,
            portfolio_value=total_portfolio_value,
            weight=weight,
            volatility=0.25,
            sector=sector,
        )

        dto = PositionRiskDTO(
            id=str(uuid4()),
            code=code,
            name=name,
            value=position_value,
            weight=round(weight * 100, 2),
            risk_level=risk_metrics.risk_level.value,
            risk_score=risk_metrics.risk_score,
            var_95=risk_metrics.value_at_risk,
            sector=sector,
        )

        if risk_metrics.risk_level == RiskLevel.HIGH:
            await self._create_alert(
                code=code,
                alert_type="position_risk_high",
                message=f"Position {code} has high risk: {risk_metrics.risk_level.value}",
                severity="high",
            )

        return dto

    async def assess_portfolio_risk(
        self,
        positions: list[dict[str, Any]],
        total_value: float,
    ) -> RiskAssessmentDTO:
        """Assess overall portfolio risk."""
        if not positions:
            return RiskAssessmentDTO(
                portfolio_value=0,
                risk_level="low",
                risk_score=0,
                var_95=0,
                var_99=0,
                expected_shortfall=0,
                max_drawdown=0,
                concentration_risk=0,
                sector_exposures={},
                warnings=[],
            )

        position_risks = []
        sector_exposure: dict[str, float] = {}

        for pos in positions:
            code = pos.get("code", "")
            value = pos.get("value", 0)
            sector = pos.get("sector", "default")

            position_risks.append({
                "code": code,
                "value": value,
                "weight": value / total_value if total_value > 0 else 0,
                "volatility": pos.get("volatility", 0.25),
            })

            sector_exposure[sector] = sector_exposure.get(sector, 0) + (value / total_value if total_value > 0 else 0)

        risk_metrics = RiskCalculator.calculate_portfolio_risk(
            positions=position_risks,
            total_value=total_value,
            confidence_level=0.95,
        )

        warnings = []

        if risk_metrics.concentration_risk > self._risk_limits["max_position_size"]:
            warnings.append(f"Position concentration exceeds {self._risk_limits['max_position_size']*100}%")

        for sector, exposure in sector_exposure.items():
            if exposure > self._risk_limits["max_sector_exposure"]:
                warnings.append(f"Sector {sector} exposure {exposure*100:.1f}% exceeds limit")

        entangled_risk = self._entangled_risk_monitor.analyze(positions, total_value)
        for pair in entangled_risk["pairs"]:
            warnings.append(
                "Entangled risk pair "
                + pair["left"]
                + "/"
                + pair["right"]
                + " correlation="
                + str(pair["semantic_correlation"])
                + " status="
                + pair["status"]
            )
        if entangled_risk["forced_reductions"]:
            await self._create_alert(
                code="portfolio",
                alert_type="entangled_risk_collapse",
                message="; ".join(item["code"] + " reduce " + str(item["reduce_weight"] * 100) + "%" for item in entangled_risk["forced_reductions"]),
                severity="high",
            )

        if warnings:
            await self._create_alert(
                code="portfolio",
                alert_type="portfolio_risk",
                message="; ".join(warnings),
                severity="medium"
            )

        return RiskAssessmentDTO(
            portfolio_value=total_value,
            risk_level=risk_metrics.risk_level.value,
            risk_score=risk_metrics.risk_score,
            var_95=risk_metrics.value_at_risk,
            var_99=risk_metrics.value_at_risk * 1.5,
            expected_shortfall=risk_metrics.expected_shortfall,
            max_drawdown=risk_metrics.max_drawdown,
            concentration_risk=risk_metrics.concentration_risk,
            sector_exposures={k: round(v * 100, 2) for k, v in sector_exposure.items()},
            warnings=warnings,
            entangled_risk=entangled_risk,
        )

    def check_trade_risk(
        self,
        code: str,
        side: str,
        quantity: int,
        price: float,
        current_positions: dict[str, int],
        portfolio_value: float,
    ) -> GenericResponseDTO:
        """Check if a trade passes risk controls."""
        trade_value = quantity * price
        new_position_value = current_positions.get(code, 0) * price
        new_total_value = new_position_value + trade_value

        weight = new_total_value / portfolio_value if portfolio_value > 0 else 0

        checks = {
            "approved": True,
            "checks": [],
            "warnings": [],
            "reasons": [],
        }

        if weight > self._risk_limits["max_position_size"]:
            checks["approved"] = False
            checks["reasons"].append(
                f"Position size {weight*100:.1f}% exceeds max {self._risk_limits['max_position_size']*100}%"
            )

        total_exposure = sum(current_positions.values()) * price
        if total_exposure > portfolio_value * self._risk_limits["max_portfolio_leverage"]:
            checks["approved"] = False
            checks["reasons"].append("Portfolio leverage limit exceeded")

        checks["checks"].append({
            "name": "position_size",
            "passed": weight <= self._risk_limits["max_position_size"],
            "value": f"{weight*100:.1f}%",
            "limit": f"{self._risk_limits['max_position_size']*100}%",
        })

        return checks

    def analyze_entangled_risk(self, positions: list[dict[str, Any]], total_value: float) -> dict[str, Any]:
        """Analyze cross-strategy semantic entanglement and joint budget collapse."""
        return self._entangled_risk_monitor.analyze(positions, total_value)

    def get_risk_limits(self) -> list[RiskLimitDTO]:
        """Get current risk limits."""
        return [
            RiskLimitDTO(name=k, value=v, description=f"Max {k.replace('_', ' ')}")
            for k, v in self._risk_limits.items()
        ]

    def update_risk_limit(self, name: str, value: float) -> bool:
        """Update a risk limit."""
        if name in self._risk_limits:
            self._risk_limits[name] = value
            return True
        return False

    def get_alerts(self, limit: int = 50) -> list[RiskAlertDTO]:
        """Get recent risk alerts."""
        return self._alerts[-limit:]

    async def _create_alert(
        self,
        code: str,
        alert_type: str,
        message: str,
        severity: str = "low",
    ):
        """Create and publish a risk alert."""
        alert = RiskAlertDTO(
            id=str(uuid4()),
            code=code,
            alert_type=alert_type,
            message=message,
            severity=severity,
            created_at=datetime.now().isoformat(),
        )
        self._alerts.append(alert)

        await publish_event(
            EventType.RISK_ALERT,
            {
                "code": code,
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
            },
            source="RiskApplicationService"
        )


from datetime import datetime

__all__ = ["RiskApplicationService"]
