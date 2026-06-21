"""Tier 3: Investment Company — Multi-Strategy Optimizer, Macro-Regime, Tax & Cost, Multi-Asset."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.logger import get_logger

logger = get_logger(__name__)

AssetClass = Literal["stock", "futures", "option", "forex", "crypto", "bond", "commodity"]


# ── Multi-Strategy Optimizer ────────────────────────────────────────

@dataclass
class StrategyAllocation:
    """Optimized allocation for a strategy."""
    strategy_id: str
    weight: float  # 0..1
    expected_return: float = 0.0
    risk_contribution: float = 0.0


@dataclass
class PortfolioOptimizationResult:
    """Portfolio-level optimization result."""
    allocations: list[StrategyAllocation] = field(default_factory=list)
    expected_return: float = 0.0
    expected_volatility: float = 0.0
    sharpe_ratio: float = 0.0


class MultiStrategyOptimizerService:
    """Multi-strategy portfolio optimization — Risk Parity & Black-Litterman."""

    def risk_parity(self, strategies: list[dict]) -> PortfolioOptimizationResult:
        """Risk Parity: equalize risk contribution from each strategy."""
        n = len(strategies)
        if n == 0:
            return PortfolioOptimizationResult()

        total_vol = sum(s.get("volatility", 1) for s in strategies)
        allocations: list[StrategyAllocation] = []
        for s in strategies:
            inv_vol = 1.0 / max(s.get("volatility", 1), 0.001)
            weight = inv_vol / max(sum(1.0 / max(x.get("volatility", 1), 0.001) for x in strategies), 0.001)
            allocations.append(StrategyAllocation(
                strategy_id=s.get("strategy_id", ""),
                weight=round(weight, 4),
                expected_return=s.get("expected_return", 0),
                risk_contribution=round(weight * s.get("volatility", 1), 4),
            ))

        port_return = sum(a.weight * a.expected_return for a in allocations)
        port_vol = math.sqrt(sum(a.risk_contribution ** 2 for a in allocations))
        return PortfolioOptimizationResult(
            allocations=allocations,
            expected_return=round(port_return, 4),
            expected_volatility=round(port_vol, 4),
            sharpe_ratio=round(port_return / max(port_vol, 0.001), 4),
        )

    def _build_correlation_matrix(self, strategies: list[dict]) -> list[list[float]]:
        n = len(strategies)
        if n == 0:
            return []
        corr = [[1.0 if i == j else 0.3 for j in range(n)] for i in range(n)]
        return corr

    def black_litterman(self, strategies: list[dict], views: list[dict],
                        tau: float = 0.05) -> PortfolioOptimizationResult:
        """Black-Litterman: blend market equilibrium with investor views."""
        n = len(strategies)
        if n == 0:
            return PortfolioOptimizationResult()

        equilibrium_weights = [1.0 / n for _ in range(n)]

        for view in views:
            sid = view.get("strategy_id", "")
            adj = view.get("adjustment", 0)
            for i, s in enumerate(strategies):
                if s.get("strategy_id") == sid:
                    equilibrium_weights[i] = max(0, equilibrium_weights[i] + adj)

        total_w = sum(equilibrium_weights)
        if total_w > 0:
            equilibrium_weights = [w / total_w for w in equilibrium_weights]

        allocations: list[StrategyAllocation] = []
        port_return = 0.0
        port_risk = 0.0
        for i, s in enumerate(strategies):
            w = round(equilibrium_weights[i], 4)
            ret = s.get("expected_return", 0)
            vol = s.get("volatility", 1)
            rc = w * vol
            allocations.append(StrategyAllocation(
                strategy_id=s.get("strategy_id", ""),
                weight=w, expected_return=ret, risk_contribution=round(rc, 4),
            ))
            port_return += w * ret
            port_risk += rc ** 2

        return PortfolioOptimizationResult(
            allocations=allocations,
            expected_return=round(port_return, 4),
            expected_volatility=round(math.sqrt(port_risk), 4),
            sharpe_ratio=round(port_return / max(math.sqrt(port_risk), 0.001), 4),
        )


# ── Macro Regime ────────────────────────────────────────────────────

@dataclass
class MacroRegime:
    """Detected macro regime."""
    regime: str  # bullish / bearish / neutral / recession / growth / turbulent
    confidence: float = 0.0
    turbulence_index: float = 0.0
    indicators: dict[str, float] = field(default_factory=dict)


class MacroRegimeService:
    """Macro regime detection and transition analysis."""

    def analyze(self, indicators: dict[str, float]) -> MacroRegime:
        """Detect macro regime from economic indicators."""
        gdp_growth = indicators.get("gdp_growth", 0)
        inflation = indicators.get("inflation", 0)
        unemployment = indicators.get("unemployment", 0)
        vix = indicators.get("vix", 20)
        interest_rate = indicators.get("interest_rate", 0)

        turbulence = min(1.0, vix / 50)

        if gdp_growth > 0.03 and inflation < 0.03:
            regime = "growth"
            confidence = min(1.0, gdp_growth * 10)
        elif gdp_growth > 0.02 and inflation < 0.05:
            regime = "bullish"
            confidence = 0.7
        elif gdp_growth < 0 and inflation > 0.05:
            regime = "stagflation"
            confidence = 0.8
        elif gdp_growth < 0:
            regime = "recession"
            confidence = min(1.0, abs(gdp_growth) * 5)
        elif inflation > 0.05:
            regime = "bearish"
            confidence = 0.6
        else:
            regime = "neutral"
            confidence = 0.5

        if turbulence > 0.6:
            regime = "turbulent"
            confidence = max(confidence, turbulence)

        return MacroRegime(
            regime=regime,
            confidence=round(confidence, 4),
            turbulence_index=round(turbulence, 4),
            indicators=indicators,
        )

    def detect_transition(self, current_indicators, previous_regime=None):
        """Detect macro regime transition signal."""
        regime = self.analyze(current_indicators)
        r = regime.__dict__ if hasattr(regime, '__dict__') else regime
        transitions = {"bearish_to_bullish": False, "bullish_to_bearish": False, "stable_to_turbulent": False}
        if previous_regime:
            prev_name = previous_regime.get("regime", "") if isinstance(previous_regime, dict) else ""
            curr_name = r.get("regime", "")
            if prev_name in ("bearish", "recession") and curr_name in ("bullish", "growth"):
                transitions["bearish_to_bullish"] = True
            elif prev_name in ("bullish", "growth") and curr_name in ("bearish", "recession"):
                transitions["bullish_to_bearish"] = True
            if r.get("turbulence_index", 0) > 0.6 and previous_regime.get("turbulence_index", 0) < 0.4:
                transitions["stable_to_turbulent"] = True
        r["transitions"] = transitions
        r["has_transition"] = any(transitions.values())
        return r


# ── Tax & Cost Optimizer ────────────────────────────────────────────

@dataclass
class TaxCostReport:
    """Tax and trading cost analysis."""
    total_tax: float = 0.0
    total_fees: float = 0.0
    total_slippage: float = 0.0
    net_return: float = 0.0
    tax_rate_used: float = 0.0
    recommendations: list[str] = field(default_factory=list)


class TaxCostOptimizerService:
    """Tax-aware and cost-aware trading optimization."""

    def optimize(self, trades: list[dict], tax_rate: float = 0.2,
                 fee_rate: float = 0.0003, slippage_bps: float = 5.0) -> TaxCostReport:
        """Compute tax and cost impact on trading."""
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        total_volume = sum(t.get("volume", 0) for t in trades)
        total_fees = total_volume * fee_rate
        total_slippage = total_volume * slippage_bps / 10000
        total_tax = max(0, total_pnl * tax_rate)

        recs = []
        if total_tax > total_pnl * 0.3:
            recs.append("Consider tax-loss harvesting to offset gains")
        if total_fees > total_pnl * 0.05:
            recs.append("Trade size too small relative to fees — consolidate orders")
        if slippage_bps > 10:
            recs.append("High slippage detected — use limit orders and TWAP")

        return TaxCostReport(
            total_tax=round(total_tax, 2),
            total_fees=round(total_fees, 2),
            total_slippage=round(total_slippage, 2),
            net_return=round(total_pnl - total_tax - total_fees - total_slippage, 2),
            tax_rate_used=tax_rate,
            recommendations=recs,
        )

    def tax_loss_harvesting(self, positions, max_loss_pct=0.05, min_hold_days=30):
        """Identify tax-loss harvesting opportunities."""
        results = []
        for pos in positions:
            symbol = pos.get("symbol", "")
            unrealized_loss = abs(pos.get("unrealized_pnl", 0))
            cost_basis = pos.get("cost_basis", 1)
            loss_pct = unrealized_loss / max(cost_basis, 1)
            if loss_pct > max_loss_pct:
                results.append({
                    "symbol": symbol,
                    "unrealized_loss": round(unrealized_loss, 2),
                    "loss_pct": round(loss_pct, 4),
                    "recommendation": "harvest",
                    "estimated_tax_benefit": round(unrealized_loss * 0.2, 2),
                    "wash_sale_risk": "low",
                })
        return {
            "opportunities": results,
            "total_harvestable_loss": round(sum(r["unrealized_loss"] for r in results), 2),
            "total_tax_benefit": round(sum(r.get("estimated_tax_benefit", 0) for r in results), 2),
        }


# ── Multi-Asset Support ─────────────────────────────────────────────

@dataclass
class MultiAssetPosition:
    """A position in any asset class."""
    position_id: str
    symbol: str
    asset_class: AssetClass
    quantity: int
    entry_price: float
    current_price: float
    pnl: float = 0.0
    delta: float = 0.0


class MultiAssetService:
    """Cross-asset hedging and multi-market support."""

    def compute_cross_hedge(self, positions: list[dict]) -> dict:
        """Compute cross-asset hedge ratios."""
        total_delta = sum(p.get("delta", 0) * p.get("quantity", 0) for p in positions)
        total_value = sum(p.get("quantity", 0) * p.get("current_price", 0) for p in positions)

        hedge_suggestions = []
        by_class: dict[str, float] = {}
        for p in positions:
            ac = p.get("asset_class", "stock")
            val = p.get("quantity", 0) * p.get("current_price", 0)
            by_class[ac] = by_class.get(ac, 0) + val

        if "option" in by_class and abs(total_delta) > 0:
            hedge_suggestions.append({
                "type": "delta_hedge",
                "delta_exposure": round(total_delta, 2),
                "suggestion": f"{'sell' if total_delta > 0 else 'buy'} {abs(total_delta)} shares of underlying",
            })

        net_fx_exposure = by_class.get("forex", 0) - by_class.get("crypto", 0)
        if abs(net_fx_exposure) > 10000:
            hedge_suggestions.append({
                "type": "fx_hedge",
                "fx_exposure": round(net_fx_exposure, 2),
                "suggestion": f"Hedge {abs(net_fx_exposure):.0f} FX exposure via forward",
            })

        return {
            "total_value": round(total_value, 2),
            "total_delta": round(total_delta, 2),
            "allocation_by_class": {k: round(v, 2) for k, v in by_class.items()},
            "hedge_suggestions": hedge_suggestions,
            "diversification_score": round(len(by_class) / 7, 4),
        }

    def market_neutral_hedge(self, long_positions, short_positions):
        """Compute optimal hedge for a market-neutral strategy."""
        long_beta = sum(p.get("beta", 1.0) * p.get("value", 0) for p in long_positions) / max(sum(p.get("value", 0) for p in long_positions), 1)
        short_beta = sum(p.get("beta", 1.0) * p.get("value", 0) for p in short_positions) / max(sum(p.get("value", 0) for p in short_positions), 1)
        net_beta = long_beta - short_beta
        total_value = sum(p.get("value", 0) for p in long_positions)
        hedge_value = abs(net_beta) * total_value
        return {
            "long_beta": round(long_beta, 4),
            "short_beta": round(short_beta, 4),
            "net_beta": round(net_beta, 4),
            "hedge_required_value": round(hedge_value, 2),
            "is_market_neutral": abs(net_beta) < 0.1,
            "recommendation": "hedge with index futures" if abs(net_beta) > 0.1 else "already neutral",
        }

    def cross_currency_hedge(self, base_currency, exposures):
        """Compute cross-currency hedging ratios."""
        total_base = sum(e.get("value_base", 0) for e in exposures)
        hedges = []
        for e in exposures:
            currency = e.get("currency", "")
            value = e.get("value_base", 0)
            if value > 0 and currency != base_currency:
                hedges.append({
                    "currency": currency,
                    "exposure": round(value, 2),
                    "hedge_pct": 0.8,
                    "suggested_instrument": f"{currency}_FX_fwd",
                    "cost_bps": 15,
                })
        return {
            "base_currency": base_currency,
            "total_exposure": round(total_base, 2),
            "hedges": hedges,
            "total_hedge_cost_bps": sum(h.get("cost_bps", 0) for h in hedges),
        }
