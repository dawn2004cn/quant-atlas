"""Market impact model service - institutional order impact forecasting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class ImpactForecast:
    """Market impact forecast for a large order."""
    symbol: str
    order_value_usd: float
    side: str  # buy / sell
    estimated_impact_bps: float
    estimated_slippage_bps: float
    liquidity_score: float  # 0..1
    suggested_speed: str  # slow / normal / urgent
    expected_price_movement_pct: float
    confidence: float = 0.0


class MarketImpactModelService:
    """Market impact forecasting for large institutional orders."""

    def forecast(
        self,
        symbol: str,
        order_value_usd: float,
        side: str = "buy",
        avg_daily_volume_usd: float = 10_000_000,
        volatility: float = 0.02,
    ) -> ImpactForecast:
        """Forecast market impact of a large order using square-root model."""
        participation_rate = order_value_usd / max(avg_daily_volume_usd, 1)

        # Square-root impact model: impact ~ sqrt(participation)
        raw_impact = 100 * volatility * math.sqrt(participation_rate)
        impact_bps = raw_impact * 100  # convert to bps

        # Slippage is typically 0.5-1.5x of impact
        slippage_bps = impact_bps * (0.8 if side == "buy" else 1.2)

        # Liquidity score
        liquidity_score = max(0, min(1, 1 - participation_rate * 5))

        # Suggested execution speed
        if impact_bps > 50:
            speed = "slow"
        elif impact_bps > 20:
            speed = "normal"
        else:
            speed = "urgent"

        return ImpactForecast(
            symbol=symbol,
            order_value_usd=order_value_usd,
            side=side,
            estimated_impact_bps=round(impact_bps, 2),
            estimated_slippage_bps=round(slippage_bps, 2),
            liquidity_score=round(liquidity_score, 4),
            suggested_speed=speed,
            expected_price_movement_pct=round(impact_bps / 100, 4),
            confidence=round(max(0, 1 - participation_rate), 3),
        )

    def forecast_almgren_chriss(
        self,
        symbol: str,
        order_value_usd: float,
        side: str = "buy",
        price: float = 100.0,
        avg_daily_volume_usd: float = 10_000_000,
        volatility: float = 0.02,
        trading_days: int = 1,
        spread_bps: float = 5.0,
    ) -> dict:
        """Almgren-Chriss impact model: permanent + temporary decomposition."""
        participation = order_value_usd / max(avg_daily_volume_usd, 1)
        sigma = volatility * math.sqrt(trading_days)

        # Permanent impact (information leakage): gamma * sigma * sign
        gamma = 0.1
        permanent_bps = gamma * sigma * 10000 * (1 if side == "buy" else -1)

        # Temporary impact (liquidity demand): eta * sigma * participation^beta
        eta = 0.3
        beta = 0.6
        temporary_bps = eta * sigma * math.pow(participation, beta) * 10000

        total_bps = abs(permanent_bps) + temporary_bps
        slippage_cost = total_bps / 10000 * order_value_usd

        return {
            "symbol": symbol,
            "order_value_usd": order_value_usd,
            "side": side,
            "participation_rate": round(participation, 6),
            "permanent_impact_bps": round(permanent_bps, 4),
            "temporary_impact_bps": round(temporary_bps, 4),
            "total_impact_bps": round(total_bps, 4),
            "slippage_cost_usd": round(slippage_cost, 2),
            "spread_bps": spread_bps,
            "confidence": round(max(0, 1 - participation * 3), 3),
        }

    def forecast_multi_asset(self, orders: list[dict]) -> dict:
        """Portfolio-level impact forecast across multiple assets."""
        results = []
        total_slippage = 0.0
        total_value = 0.0
        for o in orders:
            result = self.forecast_almgren_chriss(
                symbol=o.get("symbol", ""),
                order_value_usd=float(o.get("order_value_usd", 0)),
                side=o.get("side", "buy"),
                price=float(o.get("price", 100)),
                avg_daily_volume_usd=float(o.get("avg_daily_volume_usd", 10_000_000)),
                volatility=float(o.get("volatility", 0.02)),
                spread_bps=float(o.get("spread_bps", 5)),
            )
            results.append(result)
            total_slippage += result["slippage_cost_usd"]
            total_value += result["order_value_usd"]
        return {
            "orders": results,
            "total_value_usd": round(total_value, 2),
            "total_slippage_usd": round(total_slippage, 2),
            "weighted_avg_impact_bps": round(
                total_slippage / max(total_value, 1) * 10000, 4
            ) if total_value > 0 else 0,
            "num_assets": len(orders),
        }
