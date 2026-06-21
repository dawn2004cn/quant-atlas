from __future__ import annotations

"""Unified attribution: style + factor + execution slippage in one report."""

import asyncio
from typing import Any

from app.modules.strategy.services.analytics.attribution_service import AttributionAnalyzer
from app.modules.system.services.helpers.portfolio_access import create_default_attribution_analysis
from app.domain.dto.analytics_dto import (
    AttributionReportDTO,
    FactorContributionDTO,
    MarketEffectDTO,
    SectorContributionDTO,
    SlippageContributionDTO,
    StockContributionDTO,
    StyleContributionDTO,
)


class UnifiedAttributionService:
    """Build ``AttributionReportDTO`` for portfolio or single-position analysis."""

    def __init__(self, analyzer: AttributionAnalyzer | None = None) -> None:
        self._analyzer = analyzer or AttributionAnalyzer()

    def build_report(
        self,
        *,
        strategy_name: str,
        period: str,
        positions: list[dict[str, Any]],
        benchmark_return: float = 0.0,
        symbol: str | None = None,
        strategy_id: str | None = None,
        portfolio_return: float | None = None,
        factor_exposures: dict[str, float] | None = None,
        factor_returns: dict[str, float] | None = None,
        alpha: float = 0.0,
        include_slippage: bool = True,
    ) -> AttributionReportDTO:
        report = self._analyzer.analyze(
            strategy_name=strategy_name,
            period=period,
            positions=positions,
            benchmark_return=benchmark_return,
        )

        style_rows = self._build_style_contributions(
            portfolio_return=portfolio_return if portfolio_return is not None else report.total_return / 100.0,
            benchmark_return=benchmark_return / 100.0 if benchmark_return > 1 else benchmark_return,
            factor_exposures=factor_exposures or {},
            factor_returns=factor_returns or {},
            alpha=alpha / 100.0 if alpha > 1 else alpha,
        )

        slippage = None
        if include_slippage:
            slippage = self._load_slippage_contribution(
                symbol=symbol or self._primary_symbol(positions),
                strategy_id=strategy_id or strategy_name,
            )

        dto = self._to_dto(
            report,
            scope="position" if symbol else "portfolio",
            symbol=symbol or self._primary_symbol(positions),
            style_contributions=style_rows,
            slippage=slippage,
        )
        dto.summary = self._analyzer.generate_human_readable_summary(report)
        if slippage and slippage.notes:
            dto.summary = f"{dto.summary}\n\n⚙️ 执行：{slippage.notes}"
        return dto

    def _build_style_contributions(
        self,
        *,
        portfolio_return: float,
        benchmark_return: float,
        factor_exposures: dict[str, float],
        factor_returns: dict[str, float],
        alpha: float,
    ) -> list[StyleContributionDTO]:
        if not factor_exposures and not factor_returns and alpha == 0.0:
            return []

        try:
            port = create_default_attribution_analysis()
        except RuntimeError:
            from app.infrastructure.portfolio.optimizer import DefaultAttributionAnalysis

            port = DefaultAttributionAnalysis()

        decomposed = port.decompose(
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            factor_exposures=factor_exposures,
            factor_returns=factor_returns,
            alpha=alpha,
        )
        mapping = (
            ("alpha", "选股 Alpha"),
            ("beta_timing", "市场择时 Beta"),
            ("style_selection", "风格因子贡献"),
            ("residual", "未解释残差"),
        )
        rows: list[StyleContributionDTO] = []
        for key, label in mapping:
            value = float(decomposed.get(key, 0.0))
            rows.append(
                StyleContributionDTO(
                    component=key,
                    contribution_pct=round(value * 100, 4),
                    description=label,
                )
            )
        interpretation = decomposed.get("interpretation")
        if interpretation:
            rows.append(
                StyleContributionDTO(
                    component="interpretation",
                    contribution_pct=0.0,
                    description=str(interpretation),
                )
            )
        return rows

    def _load_slippage_contribution(
        self,
        *,
        symbol: str | None,
        strategy_id: str | None,
    ) -> SlippageContributionDTO | None:
        try:
            from app.config import get_settings

            settings = get_settings()
            if not settings.use_mysql:
                return None

            from app.infrastructure.repositories.common.deps import create_slippage_analysis_service

            service = create_slippage_analysis_service(settings)

            async def _run() -> dict[str, Any]:
                return await service.analyze_slippage(
                    symbol=symbol,
                    strategy_id=strategy_id,
                    lookback_days=30,
                )

            analysis = asyncio.run(_run())
        except Exception:
            return None

        if analysis.get("status") != "analyzed":
            return SlippageContributionDTO(
                quality=str(analysis.get("status", "no_data")),
                notes="暂无实盘成交样本",
            )

        stats = analysis.get("stats") or {}
        avg_slippage = float(stats.get("avg_slippage_pct") or 0.0)
        return SlippageContributionDTO(
            avg_slippage_pct=round(avg_slippage, 4),
            quality=str(analysis.get("quality", "unknown")),
            contribution_pct=round(-abs(avg_slippage), 4),
            latency_ms=float(stats["avg_latency_ms"]) if stats.get("avg_latency_ms") else None,
            order_count=int(stats.get("total_orders") or 0),
            notes=str((analysis.get("recommendations") or {}).get("notes") or analysis.get("quality", "")),
        )

    @staticmethod
    def _primary_symbol(positions: list[dict[str, Any]]) -> str | None:
        if not positions:
            return None
        return str(positions[0].get("symbol") or "") or None

    @staticmethod
    def _to_dto(
        report: Any,
        *,
        scope: str,
        symbol: str | None,
        style_contributions: list[StyleContributionDTO],
        slippage: SlippageContributionDTO | None,
    ) -> AttributionReportDTO:
        return AttributionReportDTO(
            strategy_name=report.strategy_name,
            period=report.period,
            scope=scope,
            symbol=symbol,
            total_return=report.total_return,
            market_effect=MarketEffectDTO(
                market_return=report.market_effect.market_return,
                alpha=report.market_effect.alpha,
                beta=report.market_effect.beta,
            ),
            factors=[
                FactorContributionDTO(
                    factor_name=f.factor_name,
                    contribution_pct=f.contribution_pct,
                    contribution_amount=f.contribution_amount,
                    description=f.description,
                )
                for f in report.factors
            ],
            style_contributions=style_contributions,
            slippage=slippage,
            sectors=[
                SectorContributionDTO(
                    sector=s.sector,
                    weight=s.weight,
                    return_pct=s.return_pct,
                    contribution_pct=s.contribution_pct,
                )
                for s in report.sectors
            ],
            stocks=[
                StockContributionDTO(
                    symbol=s.symbol,
                    name=s.name,
                    weight=s.weight,
                    return_pct=s.return_pct,
                    contribution_pct=s.contribution_pct,
                )
                for s in report.stocks
            ],
            top_contributors=[
                StockContributionDTO(
                    symbol=s.symbol,
                    name=s.name,
                    weight=s.weight,
                    return_pct=s.return_pct,
                    contribution_pct=s.contribution_pct,
                )
                for s in report.top_contributors
            ],
            bottom_contributors=[
                StockContributionDTO(
                    symbol=s.symbol,
                    name=s.name,
                    weight=s.weight,
                    return_pct=s.return_pct,
                    contribution_pct=s.contribution_pct,
                )
                for s in report.bottom_contributors
            ],
            generated_at=report.generated_at,
        )
