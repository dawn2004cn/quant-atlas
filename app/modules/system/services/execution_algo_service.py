"""Advanced execution algorithm service - VWAP, TWAP, Iceberg, POV."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionSchedule:
    """Unified execution schedule for institutional algos."""
    schedule_id: str
    algo: str  # vwap / twap / iceberg / pov
    symbol: str
    side: str
    total_quantity: int
    slices: list[dict] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class POVSchedule:
    """Percentage of Volume execution schedule."""
    schedule_id: str
    symbol: str
    side: str
    total_quantity: int
    participation_rate: float  # 0.05 = 5% of volume
    slices: list[dict] = field(default_factory=list)


class AdvancedExecutionAlgoService:
    """VWAP, TWAP, Iceberg, POV execution algorithms."""

    def generate_vwap(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        num_slices: int = 20,
        volume_profile: list[float] | None = None,
    ) -> ExecutionSchedule:
        """VWAP: slice by volume-weighted profile across the session."""
        profile = volume_profile or self._default_volume_profile(num_slices)
        total_weight = sum(profile) or 1.0
        remaining = total_quantity
        slices: list[dict] = []
        for i, weight in enumerate(profile):
            if i == len(profile) - 1:
                qty = remaining
            else:
                qty = max(1, int(total_quantity * weight / total_weight))
                remaining -= qty
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "weight_pct": round(weight / total_weight * 100, 2),
                "type": "limit",
                "note": "VWAP volume-weighted slice",
            })
        return ExecutionSchedule(
            schedule_id=f"vwap.{uuid.uuid4().hex[:8]}",
            algo="vwap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"num_slices": num_slices},
        )

    def generate_twap(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        num_slices: int = 20,
        interval_minutes: int = 5,
    ) -> ExecutionSchedule:
        """TWAP: equal quantity per time interval."""
        qty_per_slice = max(1, total_quantity // num_slices)
        slices = []
        for i in range(num_slices):
            qty = qty_per_slice if i < num_slices - 1 else total_quantity - qty_per_slice * (num_slices - 1)
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "interval_minutes": interval_minutes,
                "type": "limit",
                "note": f"TWAP every {interval_minutes}min",
            })
        return ExecutionSchedule(
            schedule_id=f"twap.{uuid.uuid4().hex[:8]}",
            algo="twap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"interval_minutes": interval_minutes, "num_slices": num_slices},
        )

    def generate_iceberg(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        display_quantity: int = 100,
        variance_pct: float = 0.1,
    ) -> ExecutionSchedule:
        """Iceberg: show small display size, replenish hidden quantity."""
        display_qty = max(1, min(display_quantity, total_quantity))
        remaining = total_quantity
        slices = []
        slice_idx = 1
        while remaining > 0:
            shown = min(display_qty, remaining)
            if variance_pct > 0:
                jitter = int(shown * variance_pct * (0.5 - (hash(f"{symbol}{slice_idx}") % 100) / 100))
                shown = max(1, shown + jitter)
                shown = min(shown, remaining)
            slices.append({
                "slice": slice_idx,
                "quantity": shown,
                "display_quantity": shown,
                "hidden": True,
                "type": "limit",
                "note": "Iceberg display slice",
            })
            remaining -= shown
            slice_idx += 1
            if slice_idx > 500:
                break
        return ExecutionSchedule(
            schedule_id=f"ice.{uuid.uuid4().hex[:8]}",
            algo="iceberg",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"display_quantity": display_qty, "variance_pct": variance_pct},
        )

    def generate_pov(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        participation_rate: float = 0.1,
        num_slices: int = 20,
    ) -> POVSchedule:
        """Generate POV execution schedule."""
        qty_per_slice = max(1, total_quantity // num_slices)
        slices = []

        for i in range(num_slices):
            qty = qty_per_slice if i < num_slices - 1 else total_quantity - qty_per_slice * (num_slices - 1)
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "participation_target": participation_rate,
                "type": "market",
                "note": f"Target {participation_rate*100:.0f}% of volume",
            })

        return POVSchedule(
            schedule_id=f"pov.{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            participation_rate=participation_rate,
            slices=slices,
        )

    def generate_adaptive(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        impact_bps: float = 0.0,
        urgency: str = "normal",
        market_volatility: float = 0.02,
    ) -> ExecutionSchedule:
        """Adaptive algo: auto-selects VWAP/TWAP/iceberg based on impact and urgency."""
        if impact_bps > 50 or urgency == "stealth":
            return self.generate_iceberg(
                symbol, side, total_quantity,
                display_quantity=max(1, total_quantity // 10),
            )
        elif impact_bps > 20 or market_volatility > 0.03:
            return self.generate_twap(symbol, side, total_quantity)
        else:
            return self.generate_vwap(symbol, side, total_quantity)

    def generate_implementation_shortfall(
        self,
        symbol: str,
        side: str,
        total_quantity: int,
        price: float,
        urgency: str = "normal",
        num_slices: int = 10,
    ) -> ExecutionSchedule:
        """Implementation Shortfall: trade off market impact vs. timing risk."""
        if urgency == "urgent":
            profile = [0.30, 0.20, 0.15, 0.10, 0.08, 0.06, 0.05, 0.03, 0.02, 0.01]
        elif urgency == "slow":
            profile = [0.02, 0.03, 0.05, 0.07, 0.10, 0.12, 0.15, 0.18, 0.18, 0.10]
        else:
            profile = [0.15, 0.15, 0.12, 0.12, 0.10, 0.10, 0.08, 0.08, 0.05, 0.05]

        total_weight = sum(profile) or 1.0
        remaining = total_quantity
        slices = []
        for i, w in enumerate(profile):
            if i == len(profile) - 1:
                qty = remaining
            else:
                qty = max(1, int(total_quantity * w / total_weight))
                remaining -= qty
            slices.append({
                "slice": i + 1,
                "quantity": qty,
                "weight_pct": round(w / total_weight * 100, 2),
                "type": "limit",
                "note": f"shortfall slice (urgency={urgency})",
            })
        return ExecutionSchedule(
            schedule_id=f"shortfall.{uuid.uuid4().hex[:8]}",
            algo="implementation_shortfall",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            slices=slices,
            params={"urgency": urgency, "arrival_price": price, "num_slices": num_slices},
        )

    @staticmethod
    def _default_volume_profile(num_slices: int) -> list[float]:
        """U-shaped intraday volume profile approximation."""
        if num_slices <= 1:
            return [1.0]
        mid = num_slices // 2
        return [
            1.5 if i < 2 or i >= num_slices - 2
            else 0.6 + 0.4 * (1 - abs(i - mid) / max(mid, 1))
            for i in range(num_slices)
        ]
