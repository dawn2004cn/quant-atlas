"""Smart Execution — SOR, VWAP/TWAP/Iceberg algorithms, Hard Circuit Breaker."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from app.core.logger import get_logger

logger = get_logger(__name__)

OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "vwap", "twap", "iceberg"]


@dataclass
class VenueProfile:
    """Execution venue profile for SOR."""
    venue_id: str
    name: str
    latency_ms: float
    fee_bps: float
    reliability: float  # 0..1
    available: bool = True


@dataclass
class ExecutionAlgorithm:
    """An execution algorithm (VWAP, TWAP, Iceberg)."""
    algo_type: OrderType
    symbol: str
    side: OrderSide
    total_quantity: int
    start_time: str
    end_time: str
    slices: list[dict] = field(default_factory=list)  # [{time, quantity, price}]
    status: str = "pending"  # pending / running / completed


@dataclass
class CircuitBreakerEvent:
    """Hard circuit breaker event — independent of AI."""
    event_id: str
    trigger: str  # daily_loss / position_limit / drawdown
    threshold: float
    current_value: float
    action: str  # warn / freeze / liquidate
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SmartOrderRouter:
    """Smart Order Routing — selects best venue based on latency, fee, reliability."""

    def __init__(self):
        self._venues: dict[str, VenueProfile] = {}

    def register_venue(self, venue: VenueProfile):
        self._venues[venue.venue_id] = venue
        logger.info("SOR venue registered: %s (latency=%.1fms, fee=%.2fbps)", venue.name, venue.latency_ms, venue.fee_bps)

    def route(self, symbol: str, side: OrderSide, quantity: int, max_latency_ms: float = 50) -> list[VenueProfile]:
        """Route an order to the best available venue(s)."""
        available = [v for v in self._venues.values() if v.available and v.latency_ms <= max_latency_ms]
        if not available:
            available = [v for v in self._venues.values() if v.available]

        # Score: lower latency + lower fee + higher reliability
        def score(v: VenueProfile) -> float:
            latency_score = max(0, 1 - v.latency_ms / 100)
            fee_score = max(0, 1 - v.fee_bps / 10)
            return latency_score * 0.4 + fee_score * 0.3 + v.reliability * 0.3

        scored = [(v, score(v)) for v in available]
        scored.sort(key=lambda x: -x[1])

        # Return top 1-2 venues
        return [v for v, _ in scored[:2]]


class ExecutionAlgorithmService:
    """VWAP, TWAP, and Iceberg execution algorithms."""

    def generate_vwap(self, symbol: str, side: OrderSide, total_quantity: int,
                      volume_profile: list[float], start: datetime, end: datetime) -> ExecutionAlgorithm:
        """Generate VWAP schedule based on historical volume profile."""
        total_vol = sum(volume_profile)
        slices = []
        interval = (end - start) / len(volume_profile)

        for i, vol_fraction in enumerate(volume_profile):
            qty = max(1, int(total_quantity * vol_fraction / total_vol))
            t = start + interval * i
            slices.append({
                "time": t.isoformat(),
                "quantity": qty,
                "price": None,  # market order
                "type": "market",
            })

        return ExecutionAlgorithm(
            algo_type="vwap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            slices=slices,
        )

    def generate_twap(self, symbol: str, side: OrderSide, total_quantity: int,
                      num_slices: int, start: datetime, end: datetime) -> ExecutionAlgorithm:
        """Generate TWAP schedule — equal slices over time."""
        qty_per_slice = max(1, total_quantity // num_slices)
        interval = (end - start) / num_slices
        slices = []

        for i in range(num_slices):
            t = start + interval * i
            qty = qty_per_slice if i < num_slices - 1 else total_quantity - qty_per_slice * (num_slices - 1)
            slices.append({
                "time": t.isoformat(),
                "quantity": qty,
                "price": None,
                "type": "market",
            })

        return ExecutionAlgorithm(
            algo_type="twap",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            slices=slices,
        )

    def generate_iceberg(self, symbol: str, side: OrderSide, total_quantity: int,
                         display_size: int, price: float) -> ExecutionAlgorithm:
        """Generate Iceberg order — shows only display_size at a time."""
        slices = []
        remaining = total_quantity
        i = 0
        while remaining > 0:
            qty = min(display_size, remaining)
            slices.append({
                "time": datetime.now(timezone.utc).isoformat(),
                "quantity": qty,
                "price": price,
                "type": "limit",
                "hidden": i > 0,  # hide after first slice
            })
            remaining -= qty
            i += 1

        return ExecutionAlgorithm(
            algo_type="iceberg",
            symbol=symbol,
            side=side,
            total_quantity=total_quantity,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            slices=slices,
        )


class HardCircuitBreaker:
    """Hard circuit breaker — independent of AI, runs on GlobalStateBus.

    Triggers:
    - Daily loss > threshold (e.g., 5%)
    - Position limit exceeded
    - Max drawdown > threshold
    """

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "circuit_breaker_log.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._daily_pnl: dict[int, float] = {}  # user_id → daily PnL
        self._daily_loss_limit = -0.05  # -5%
        self._position_limit_pct = 0.30  # max 30% in one position
        self._max_drawdown_limit = 0.20  # -20%

    def check_daily_loss(self, user_id: int, current_pnl: float, initial_capital: float) -> CircuitBreakerEvent | None:
        """Check if daily loss exceeds threshold."""
        loss_pct = current_pnl / initial_capital if initial_capital > 0 else 0
        if loss_pct <= self._daily_loss_limit:
            event = CircuitBreakerEvent(
                event_id=f"cb.{uuid.uuid4().hex[:8]}",
                trigger="daily_loss",
                threshold=self._daily_loss_limit,
                current_value=round(loss_pct, 4),
                action="liquidate",
            )
            self._log_event(event)
            logger.warning("CIRCUIT BREAKER: User %d daily loss %.2f%% (limit: %.2f%%)",
                          user_id, loss_pct * 100, self._daily_loss_limit * 100)
            return event
        return None

    def check_position_limit(self, user_id: int, symbol: str, position_value: float,
                              portfolio_value: float) -> CircuitBreakerEvent | None:
        """Check if position exceeds max allocation."""
        pct = position_value / portfolio_value if portfolio_value > 0 else 0
        if pct >= self._position_limit_pct:
            event = CircuitBreakerEvent(
                event_id=f"cb.{uuid.uuid4().hex[:8]}",
                trigger="position_limit",
                threshold=self._position_limit_pct,
                current_value=round(pct, 4),
                action="freeze",
            )
            self._log_event(event)
            logger.warning("CIRCUIT BREAKER: User %d position %s = %.1f%% (limit: %.1f%%)",
                          user_id, symbol, pct * 100, self._position_limit_pct * 100)
            return event
        return None

    def check_drawdown(self, user_id: int, current_drawdown: float) -> CircuitBreakerEvent | None:
        """Check if drawdown exceeds limit."""
        if abs(current_drawdown) >= self._max_drawdown_limit:
            event = CircuitBreakerEvent(
                event_id=f"cb.{uuid.uuid4().hex[:8]}",
                trigger="drawdown",
                threshold=self._max_drawdown_limit,
                current_value=round(current_drawdown, 4),
                action="liquidate",
            )
            self._log_event(event)
            logger.warning("CIRCUIT BREAKER: User %d drawdown %.2f%% (limit: %.2f%%)",
                          user_id, current_drawdown * 100, self._max_drawdown_limit * 100)
            return event
        return None

    def _log_event(self, event: CircuitBreakerEvent):
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")
