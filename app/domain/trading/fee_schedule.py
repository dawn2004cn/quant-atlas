"""Exchange fee schedules for backtests (SRS: tiered commission)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Side = Literal["buy", "sell"]


@dataclass(frozen=True, slots=True)
class FeeTier:
    """Apply ``rate`` when notional is in ``[min_notional, max_notional)``.

    ``max_notional`` None means unbounded.
    """

    min_notional: float
    rate: float
    max_notional: float | None = None
    min_fee: float = 0.0


@dataclass(frozen=True, slots=True)
class FeeBreakdown:
    fee_schedule_id: str
    commission: float
    stamp_tax: float
    transfer_fee: float
    total: float


@dataclass(frozen=True, slots=True)
class FeeSchedule:
    schedule_id: str
    tiers: tuple[FeeTier, ...]
    stamp_tax_sell_rate: float = 0.0
    transfer_fee_rate: float = 0.0
    description: str = ""

    def _pick_tier(self, notional: float) -> FeeTier:
        n = abs(float(notional))
        for tier in self.tiers:
            hi = tier.max_notional
            if n >= tier.min_notional and (hi is None or n < hi):
                return tier
        return self.tiers[-1]

    def calculate(self, *, notional: float, side: Side) -> FeeBreakdown:
        n = abs(float(notional))
        tier = self._pick_tier(n)
        commission = max(n * tier.rate, tier.min_fee)
        transfer = n * self.transfer_fee_rate
        stamp = n * self.stamp_tax_sell_rate if side == "sell" else 0.0
        total = commission + transfer + stamp
        return FeeBreakdown(
            fee_schedule_id=self.schedule_id,
            commission=commission,
            stamp_tax=stamp,
            transfer_fee=transfer,
            total=total,
        )


_SCHEDULES: dict[str, FeeSchedule] = {
    "cn_a_retail_v1": FeeSchedule(
        schedule_id="cn_a_retail_v1",
        description="A-share retail: tiered commission, sell stamp tax, transfer fee",
        stamp_tax_sell_rate=0.0005,
        transfer_fee_rate=0.00002,
        tiers=(
            FeeTier(0.0, 0.0003, 100_000.0, min_fee=5.0),
            FeeTier(100_000.0, 0.00025, 1_000_000.0, min_fee=5.0),
            FeeTier(1_000_000.0, 0.0002, None, min_fee=5.0),
        ),
    ),
    "crypto_flat_v1": FeeSchedule(
        schedule_id="crypto_flat_v1",
        description="Crypto flat taker fee",
        tiers=(FeeTier(0.0, 0.001, None, min_fee=0.0),),
    ),
    "us_zero_v1": FeeSchedule(
        schedule_id="us_zero_v1",
        description="US retail zero commission (SEC fee ignored)",
        tiers=(FeeTier(0.0, 0.0, None, min_fee=0.0),),
    ),
}


def list_fee_schedule_ids() -> list[str]:
    return sorted(_SCHEDULES.keys())


def get_fee_schedule(schedule_id: str) -> FeeSchedule:
    key = str(schedule_id or "").strip()
    if key not in _SCHEDULES:
        raise KeyError(f"unknown_fee_schedule:{key}")
    return _SCHEDULES[key]
