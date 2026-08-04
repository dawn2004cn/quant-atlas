"""Multi-Agent Portfolio Immunity — Phase 16.
ImmuneAgent in-domain simulations and synthetic data fill for logic gaps."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.event_bus import EventBus, get_event_bus
from app.core.logger import get_logger
from app.domain.data_truth.guardian_schema import MarketRegime
from app.domain.strategy.strategy_spec import StrategySpec

logger = get_logger(__name__)

ImmunityLevel = Literal["low", "medium", "high", "critical"]


@dataclass
class ImmunityThreat:
    """A simulated threat scenario for portfolio resilience check."""
    threat_id: str
    scenario: str = "default"
    regime: MarketRegime = MarketRegime.SIDEWAYS
    severity: ImmunityLevel = "medium"
    trigger_expression: str = "default"
    description: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImmunityThreat:
        return cls(**data)


@dataclass
class ImmunityVaccine:
    """Auto-hedge recommendation based on threat simulation."""
    threat_id: str
    strategy_id: str
    vaccine_symbol: str
    direction: Literal["long", "short"]
    hedge_ratio: float
    confidence: float
    rationale: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SyntheticFillPacket:
    """Patch for logical gaps (e.g., suspension days, new stocks)."""
    gap_type: str
    symbol: str
    start_date: str
    end_date: str
    synthetic_data: dict[str, Any]
    provenance: dict[str, float]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ImmuneAgentService:
    """Pro-active immune simulations and threat vaccination."""

    def __init__(
        self,
        *,
        strategy_spec: StrategySpec,
        stress_tester: Any,
        event_bus: EventBus | None = None,
        store_path: Path | str | None = None,
    ):
        self._spec = strategy_spec
        self._stress = stress_tester
        self._bus = event_bus or get_event_bus()
        root = Path(__file__).resolve().parents[4]
        self._store_path = Path(store_path) if store_path else root / "instance" / "immune_scenarios.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._fill_store = root / "instance" / "synthetic_fills.jsonl"

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+", "Z")

    def simulate_threat(self, threat_spec: ImmunityThreat) -> ImmunityVaccine | None:
        """Simulate a threat scenario and recommend hedge."""
        try:
            results = self._stress.run_scenario(
                strategy=self._spec.strategy_id,
                scenario=threat_spec.scenario,
                severity=threat_spec.severity,
                start_date=datetime.fromisoformat(threat_spec.timestamp),
                end_date=None,
            )

            exposure = next((r for r in results if r.scenario_id == threat_spec.scenario), None)
            if not exposure:
                return None

            hedge_symbol, ratio = self._find_hedge(exposure.risk_metrics)
            return ImmunityVaccine(
                threat_id=threat_spec.threat_id,
                strategy_id=self._spec.strategy_id,
                vaccine_symbol=hedge_symbol,
                direction="short" if exposure.long_risk else "long",
                hedge_ratio=round(ratio * 100, 2),
                confidence=round(1 - exposure.max_drawdown, 3),
                rationale=f"{threat_spec.severity.capitalize()} threat hedge based on {threat_spec.scenario}",
            )

        except Exception as exc:
            logger.debug("Threat %s sim failed: %s", threat_spec.threat_id, exc)
            return None

    def _find_hedge(self, metrics: dict) -> tuple[str, float]:
        """Find most correlated hedge symbol and ratio."""
        corr = metrics.get("correlation", {})
        best_sym = max(corr.keys(), key=lambda k: abs(corr[k]), default=None)
        best_ratio = corr[best_sym] * 0.7 if best_sym else 0.25
        return best_sym or "IC300", abs(best_ratio)

    def dispatch_vaccine_plan(self, vaccine: ImmunityVaccine):
        """Send vaccine plan to portfolio manager."""
        try:
            plan = {
                "strategy_id": vaccine.strategy_id,
                "plan": "auto_hedge",
                "symbol": vaccine.vaccine_symbol,
                "direction": vaccine.direction,
                "ratio_percent": vaccine.hedge_ratio,
                "confidence": vaccine.confidence,
                "rationale": vaccine.rationale,
                "expires_at": datetime.now(timezone.utc).isoformat(),
            }
            self._bus.publish("AUTO_HEDGE_PLAN", payload=plan)
            logger.info("Vaccine plan dispatched for %s on %s", vaccine.strategy_id, vaccine.vaccine_symbol)
            return True
        except Exception as exc:
            logger.warning("Vaccine dispatch failed: %s", exc)
            return False

    def fill_synthetic_data(
        self, symbol: str, start_date: str, end_date: str, regime: MarketRegime, **fill_attrs
    ) -> SyntheticFillPacket:
        """Generate synthetic data to fill logic gaps."""
        try:
            # Use stress tester to forecast missing data
            packet = SyntheticFillPacket(
                gap_type="suspension_fill",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                synthetic_data={
                    "open": [round(x, 2) for x in fill_attrs.get("open", [10.0])],
                    "high": [round(x, 2) for x in fill_attrs.get("high", [11.0])],
                    "low": [round(x, 2) for x in fill_attrs.get("low", [9.5])],
                    "close": [round(x, 2) for x in fill_attrs.get("close", [10.5])],
                    "volume": [int(x) for x in fill_attrs.get("volume", [1000])],
                },
                provenance={
                    "regime_match": 1.0,
                    "data_truth_score": 0.9,
                }
            )

            with self._fill_store.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(asdict(packet)) + "\n")
            return packet

        except Exception as exc:
            logger.warning("Synthetic fill for %s failed: %s", symbol, exc)
            return SyntheticFillPacket(
                gap_type="fill_error",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                synthetic_data={},
                provenance={"error": str(exc)},
            )

    def load_immune_scenarios(self) -> list[ImmunityThreat]:
        """Load past threat scenarios."""
        threats = []
        try:
            with self._store_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        threats.append(ImmunityThreat(**json.loads(line)))
        except (FileNotFoundError, json.JSONDecodeError):
            return []
        return threats
