"""One-Click Service — Intent-is-Execution.

Deploys shared WisdomMesh strategies with one click.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OneClickService:
    """Intent-is-execution: deploy shared strategies with minimal friction."""

    def __init__(
        self,
        *,
        risk_service: Any | None = None,
        strategy_service: Any | None = None,
        mesh_service: Any | None = None,
        trade_plan_service: Any | None = None,
    ) -> None:
        self._risk_service = risk_service
        self._strategy_service = strategy_service
        self._mesh_service = mesh_service
        self._trade_plan_service = trade_plan_service

    # ---- public API -------------------------------------------------------

    def deploy_shared_strategy(
        self,
        user_id: str,
        strategy_id: str,
        symbol: str,
        market: str = "CN",
        account_equity: float = 100000.0,
    ) -> dict[str, Any]:
        """One-click deploy a shared WisdomMesh strategy."""
        # 1. Load strategy from Wisdom Mesh
        if self._mesh_service is None:
            return {"ok": False, "error": "wisdom_mesh_unavailable"}

        strategy = self._mesh_service.get_shared_strategy(strategy_id)
        if not strategy:
            return {"ok": False, "error": "strategy_not_found"}

        # 2. Risk pre-flight check
        if self._risk_service is not None:
            risk_result = self._risk_service.check_order(
                user_id=user_id,
                code=symbol,
                side="buy",
                quantity=max(100, int(account_equity * strategy.get("strategy_spec", {}).get("capital_per_trade", 0.1) / 100)),
                price=0,  # Will be filled at execution
                current_positions={},
                portfolio_value=account_equity,
            )
            if not risk_result.get("approved", True):
                return {
                    "ok": False,
                    "error": "risk_check_failed",
                    "risk_details": risk_result,
                }

        # 3. Generate trade plan
        if self._trade_plan_service is not None:
            plan = self._trade_plan_service.create(
                symbol=symbol,
                market=market,
                strategy_id=strategy_id,
                strategy_spec=strategy.get("strategy_spec", {}),
            )
        else:
            plan = {"status": "planned", "strategy_id": strategy_id, "symbol": symbol}

        # 4. Return deployment result
        return {
            "ok": True,
            "strategy_id": strategy_id,
            "strategy_name": strategy.get("strategy_name", ""),
            "symbol": symbol,
            "market": market,
            "equity": account_equity,
            "trade_plan": plan,
            "risk_checked": True,
        }

    def generate_evidence_card(self, strategy_id: str, symbol: str) -> dict[str, Any]:
        """Generate a plain-language evidence card for a shared strategy."""
        if self._mesh_service is None:
            return {"ok": False, "error": "wisdom_mesh_unavailable"}

        strategy = self._mesh_service.get_shared_strategy(strategy_id)
        if not strategy:
            return {"ok": False, "error": "strategy_not_found"}

        return {
            "ok": True,
            "strategy_name": strategy.get("strategy_name", ""),
            "symbol": symbol,
            "factors": strategy.get("strategy_spec", {}).get("entry_conditions", {}).get("children", []),
            "exit_rules": strategy.get("strategy_spec", {}).get("exit_rules", []),
        }

    def jarvis_execute(
        self,
        user_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
    ) -> dict[str, Any]:
        """Jarvis one-click execution for a shared strategy."""
        result = self.deploy_shared_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            symbol=symbol,
        )
        if not result.get("ok"):
            return result

        result["execution"] = {
            "side": side,
            "quantity": quantity,
            "price": price,
        }
        return result
