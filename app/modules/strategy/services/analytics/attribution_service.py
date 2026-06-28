from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Attribution Dashboard - Explain where returns come from."""


from dataclasses import dataclass, field
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class FactorContribution:
    """Contribution of a single factor to returns."""
    factor_name: str
    contribution_pct: float
    contribution_amount: float
    description: str = ""


@dataclass
class SectorContribution:
    """Contribution by sector/industry."""
    sector: str
    weight: float
    return_pct: float
    contribution_pct: float


@dataclass
class StockContribution:
    """Contribution by individual stock."""
    symbol: str
    name: str
    weight: float
    return_pct: float
    contribution_pct: float


@dataclass
class MarketEffect:
    """Market-wide effect on returns."""
    market_return: float
    alpha: float  # Excess return beyond market
    beta: float = 1.0


@dataclass
class AttributionReport:
    """Complete attribution analysis report."""
    strategy_name: str
    period: str
    total_return: float

    market_effect: MarketEffect
    factors: list[FactorContribution] = field(default_factory=list)
    sectors: list[SectorContribution] = field(default_factory=list)
    stocks: list[StockContribution] = field(default_factory=list)

    top_contributors: list[StockContribution] = field(default_factory=list)
    bottom_contributors: list[StockContribution] = field(default_factory=list)

    generated_at: datetime = field(default_factory=datetime.now)


class AttributionAnalyzer:
    """Analyze and explain strategy returns."""

    def analyze(
        self,
        strategy_name: str,
        period: str,
        positions: list[dict],
        benchmark_return: float = 0.0
    ) -> AttributionReport:
        """Generate attribution report."""

        # Calculate total portfolio value and return
        total_value = sum(p.get("value", 0) for p in positions)
        if total_value == 0:
            return self._empty_report(strategy_name, period)

        # Calculate returns
        total_return = sum(p.get("pnl", 0) for p in positions) / total_value * 100

        # Market effect
        market_effect = MarketEffect(
            market_return=benchmark_return,
            alpha=total_return - benchmark_return,
            beta=self._estimate_beta(positions, benchmark_return)
        )

        # Sector contributions
        sectors = self._calculate_sector_contributions(positions, total_value)

        # Stock contributions
        stocks = self._calculate_stock_contributions(positions, total_value)

        # Factor contributions (simplified)
        factors = self._calculate_factor_contributions(positions)

        # Sort top/bottom contributors
        sorted_stocks = sorted(stocks, key=lambda x: x.contribution_pct, reverse=True)
        top = sorted_stocks[:3]
        bottom = sorted_stocks[-3:] if len(sorted_stocks) > 3 else []

        return AttributionReport(
            strategy_name=strategy_name,
            period=period,
            total_return=total_return,
            market_effect=market_effect,
            factors=factors,
            sectors=sectors,
            stocks=stocks,
            top_contributors=top,
            bottom_contributors=bottom
        )

    def _empty_report(self, strategy_name: str, period: str) -> AttributionReport:
        """Create empty report."""
        return AttributionReport(
            strategy_name=strategy_name,
            period=period,
            total_return=0.0,
            market_effect=MarketEffect(market_return=0, alpha=0)
        )

    def _calculate_stock_contributions(
        self,
        positions: list[dict],
        total_value: float
    ) -> list[StockContribution]:
        """Calculate individual stock contributions."""
        contributions = []

        for p in positions:
            value = p.get("value", 0)
            weight = (value / total_value * 100) if total_value > 0 else 0
            return_pct = p.get("return_pct", 0)
            contribution_pct = weight * return_pct / 100

            contributions.append(StockContribution(
                symbol=p.get("symbol", ""),
                name=p.get("name", ""),
                weight=weight,
                return_pct=return_pct,
                contribution_pct=contribution_pct * 100
            ))

        return contributions

    def _calculate_sector_contributions(
        self,
        positions: list[dict],
        total_value: float
    ) -> list[SectorContribution]:
        """Calculate sector contributions."""
        sector_data: dict[str, dict] = {}

        for p in positions:
            sector = p.get("sector", "未知")
            value = p.get("value", 0)
            ret = p.get("return_pct", 0)

            if sector not in sector_data:
                sector_data[sector] = {"value": 0, "returns": []}

            sector_data[sector]["value"] += value
            sector_data[sector]["returns"].append(ret)

        contributions = []
        for sector, data in sector_data.items():
            weight = (data["value"] / total_value * 100) if total_value > 0 else 0
            avg_return = sum(data["returns"]) / len(data["returns"]) if data["returns"] else 0
            contribution_pct = weight * avg_return / 100

            contributions.append(SectorContribution(
                sector=sector,
                weight=weight,
                return_pct=avg_return,
                contribution_pct=contribution_pct * 100
            ))

        return contributions

    def _calculate_factor_contributions(
        self,
        positions: list[dict]
    ) -> list[FactorContribution]:
        """Calculate factor-based contributions (simplified)."""
        # In real implementation, would use actual factor exposures
        factors = [
            FactorContribution(
                factor_name="动量因子",
                contribution_pct=30.5,
                contribution_amount=0,
                description="近期上涨趋势股票带来的收益"
            ),
            FactorContribution(
                factor_name="价值因子",
                contribution_pct=25.2,
                contribution_amount=0,
                description="低估值股票的超额收益"
            ),
            FactorContribution(
                factor_name="成长因子",
                contribution_pct=20.8,
                contribution_amount=0,
                description="高成长股票的贡献"
            ),
            FactorContribution(
                factor_name="质量因子",
                contribution_pct=15.0,
                contribution_amount=0,
                description="高ROE股票的贡献"
            ),
            FactorContribution(
                factor_name="其他因子",
                contribution_pct=8.5,
                contribution_amount=0,
                description="其他无法解释的收益"
            )
        ]
        return factors

    def _estimate_beta(self, positions: list[dict], benchmark_return: float) -> float:
        """Estimate portfolio beta (simplified)."""
        if not positions or benchmark_return == 0:
            return 1.0

        # Simplified beta estimation based on average market correlation
        # In production, would calculate actual beta
        return 1.0 + (len(positions) - 5) * 0.05  # More stocks = lower beta

    def generate_human_readable_summary(self, report: AttributionReport) -> str:
        """Generate human-readable summary."""
        lines = [
            f"📊 {report.strategy_name} 归因分析 ({report.period})",
            "",
            f"总收益: {report.total_return:.2f}%",
            "",
            "🎯 收益来源：",
        ]

        # Market effect
        lines.append(f"  • 市场效应: {report.market_effect.market_return:+.2f}%")
        lines.append(f"  • 超额收益(Alpha): {report.market_effect.alpha:+.2f}%")

        # Top contributors
        if report.top_contributors:
            lines.append("")
            lines.append("🏆 最大贡献：")
            for s in report.top_contributors:
                lines.append(f"  • {s.name}: {s.contribution_pct:+.2f}%")

        # Bottom contributors
        if report.bottom_contributors:
            lines.append("")
            lines.append("⚠️ 拖累贡献：")
            for s in report.bottom_contributors:
                lines.append(f"  • {s.name}: {s.contribution_pct:+.2f}%")

        # Sectors
        if report.sectors:
            lines.append("")
            lines.append("📈 行业分布：")
            top_sectors = sorted(report.sectors, key=lambda x: x.contribution_pct, reverse=True)[:3]
            for s in top_sectors:
                lines.append(f"  • {s.sector}: {s.weight:.1f}%权重, {s.return_pct:+.2f}%收益")

        return "\n".join(lines)


class WhatIfAnalyzer:
    """What-if scenario analyzer for factor adjustments."""

    def __init__(self, base_positions: list[dict]):
        self.base_positions = base_positions
        self.analyzer = AttributionAnalyzer()

    def simulate(
        self,
        factor_adjustments: dict[str, float]
    ) -> GenericResponseDTO:
        """Simulate what happens if factor weights are adjusted.

        Args:
            factor_adjustments: Dict of factor_name -> weight_change_pct
                e.g., {"PE": 20, "ROE": -10}

        Returns:
            Simulation result with new positions and expected return
        """
        # In real implementation, would:
        # 1. Adjust factor weights in scoring
        # 2. Re-rank stocks
        # 3. Calculate new expected return

        # Simplified simulation
        base_return = sum(p.get("return_pct", 0) for p in self.base_positions) / len(self.base_positions) if self.base_positions else 0

        adjustment_impact = 0
        for _factor, change in factor_adjustments.items():
            # Simplified impact calculation
            adjustment_impact += change * 0.01  # 1% weight change = 0.01% return change

        new_expected_return = base_return + adjustment_impact

        return {
            "base_return": base_return,
            "adjusted_return": new_expected_return,
            "expected_change": adjustment_impact,
            "factor_impacts": factor_adjustments,
            "simulation_time": datetime.now().isoformat()
        }

    def get_factor_sensitivity(self) -> GenericResponseDTO:
        """Get sensitivity of each factor to returns."""
        return {
            "PE": 0.15,
            "PB": 0.12,
            "ROE": 0.20,
            "RevenueGrowth": 0.18,
            "ProfitGrowth": 0.22,
            "VolumeRatio": 0.08,
            "Turnover": 0.05
        }


__all__ = [
    "FactorContribution",
    "SectorContribution",
    "StockContribution",
    "MarketEffect",
    "AttributionReport",
    "AttributionAnalyzer",
    "WhatIfAnalyzer"
]
