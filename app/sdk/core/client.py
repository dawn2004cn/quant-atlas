from __future__ import annotations

"""Quant Atlas SDK: high-level client and strategy helpers."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.modules.strategy.services.analytics.unified_attribution_service import UnifiedAttributionService
from app.modules.strategy.services.strategy.strategy_snapshot_service import StrategySnapshotService
from app.modules.system.services.system.alert_center_service import AlertCenterService
from app.sdk.facades.alerts import AlertsFacade
from app.sdk.facades.attribution import AttributionFacade
from app.sdk.facades.snapshots import SnapshotsFacade


@dataclass
class StrategyDefinition:
    """Type-safe strategy definition."""

    name: str
    symbol: str
    lookback: int = 20


def strategy(name: str, symbol: str, lookback: int = 20):
    """Decorator to define a strategy."""

    def decorator(func: Callable):
        func._is_strategy = True
        func._strategy_meta = StrategyDefinition(name, symbol, lookback)
        return func

    return decorator


class QuantAtlasClient:
    """Entry point for scripts, notebooks, and external integrations."""

    def __init__(
        self,
        *,
        swarm_service: Any | None = None,
        attribution_service: UnifiedAttributionService | None = None,
        alert_service: AlertCenterService | None = None,
        snapshot_service: StrategySnapshotService | None = None,
    ) -> None:
        self._swarm = swarm_service
        self._attribution = AttributionFacade(attribution_service)
        self._alerts = AlertsFacade(alert_service)
        self._snapshots = SnapshotsFacade(snapshot_service)

    @property
    def attribution(self) -> AttributionFacade:
        return self._attribution

    @property
    def alerts(self) -> AlertsFacade:
        return self._alerts

    @property
    def snapshots(self) -> SnapshotsFacade:
        return self._snapshots

    @property
    def swarm(self) -> Any | None:
        return self._swarm

    def run_strategy(self, strategy_func: Callable, symbol: str) -> dict[str, Any]:
        """Execute a strategy using the Swarm Orchestrator when configured."""
        if self._swarm is None:
            raise RuntimeError("swarm_service_not_configured")
        return self._swarm.start_research_swarm(
            symbol=symbol,
            preset="strategy_audit_preset",
        )


def create_client(**kwargs: Any) -> QuantAtlasClient:
    """Factory for ``QuantAtlasClient`` with optional service overrides."""
    return QuantAtlasClient(**kwargs)
