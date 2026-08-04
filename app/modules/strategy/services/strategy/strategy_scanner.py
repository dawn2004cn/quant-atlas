from __future__ import annotations

"""Automated strategy signal scanner."""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


class AutomatedStrategyScanner:
    """Monitors strategies and identifies potential trading signals."""

    def __init__(self, swarm_service: Any) -> None:
        self._swarm_service = swarm_service

    @property
    def swarm_service(self) -> Any:
        return self._swarm_service

    def scan_strategies(self, symbol_list: list[str]) -> list[dict[str, Any]]:
        """Run strategy presets against a list of symbols."""
        results = []
        presets = self.swarm_service.swarm_port.list_presets()
        strategy_presets = [p for p in presets if "strategy" in p.lower()]

        logger.info("Scanning %s strategies across %s symbols", len(strategy_presets), len(symbol_list))

        for preset in strategy_presets:
            for symbol in symbol_list:
                res = self.swarm_service.start_research_swarm(
                    symbol=symbol,
                    topic=f"Scan for entry signals for {symbol} using strategy {preset}",
                    preset=preset,
                )
                results.append({"preset": preset, "symbol": symbol, "run_id": res.get("id")})

        return results
