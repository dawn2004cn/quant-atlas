from __future__ import annotations
"""Risk policy domain models."""


from dataclasses import dataclass
from typing import Any


@dataclass
class RiskPolicy:
    """Risk policy entity with pure business rules."""
    
    max_loss_pct: float = 5.0
    max_position_pct: float = 15.0
    stop_loss_pct: float = 7.0
    take_profit_pct: float = 15.0
    
    def assess_risk(
        self,
        entry_price: float,
        current_price: float,
        position_size: float,
    ) -> dict[str, Any]:
        """Assess risk for a position."""
        if entry_price <= 0:
            return {"level": "invalid", "signal": "neutral", "loss_pct": 0.0}
        
        loss_pct = (1 - current_price / entry_price) * 100
        
        if loss_pct >= self.max_loss_pct:
            return {"level": "critical", "signal": "exit", "loss_pct": loss_pct}
        elif loss_pct >= self.max_loss_pct * 0.6:
            return {"level": "warning", "signal": "monitor", "loss_pct": loss_pct}
        
        profit_pct = (current_price / entry_price - 1) * 100
        if profit_pct >= self.take_profit_pct:
            return {"level": "profit", "signal": "take_profit", "profit_pct": profit_pct}
        
        return {"level": "normal", "signal": "hold", "loss_pct": 0.0}

    def calculate_position_size(
        self,
        account_equity: float,
        entry_price: float,
        risk_amount: float | None = None,
    ) -> int:
        """Calculate recommended position size."""
        risk = risk_amount or (account_equity * self.max_loss_pct / 100)
        max_shares = int(risk / (entry_price * self.stop_loss_pct / 100))
        return (max_shares // 100) * 100

    def should_stop_loss(self, entry_price: float, current_price: float) -> bool:
        """Determine if stop-loss should be triggered."""
        if entry_price <= 0:
            return False
        return (1 - current_price / entry_price) >= (self.stop_loss_pct / 100)

    def should_take_profit(self, entry_price: float, current_price: float) -> bool:
        """Determine if take-profit should be triggered."""
        if entry_price <= 0:
            return False
        return (current_price / entry_price - 1) >= (self.take_profit_pct / 100)