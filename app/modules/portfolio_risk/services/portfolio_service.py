from __future__ import annotations
"""Portfolio management application service."""


from datetime import datetime
from typing import Any

from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode
from app.domain.ports import (
    PortfolioOptimizerPort,
    AttributionAnalysisPort,
    PortfolioAsset,
    MarketDataProvider,
)
from app.modules.system.services.helpers.portfolio_access import (
    create_default_attribution_analysis,
    create_markowitz_optimizer,
)
from app.application.dto.portfolio_dto import (
    PortfolioSnapshotDTO,
    OptimizationRequestDTO,
    OptimizationResultDTO,
    RebalanceAlertDTO,
    AttributionResultDTO,
    PortfolioPositionDTO,
)


class PortfolioApplicationService(BaseApplicationService):
    """Application service for portfolio management."""

    def __init__(
        self,
        market_provider: MarketDataProvider,
        optimizer: PortfolioOptimizerPort | None = None,
        attribution: AttributionAnalysisPort | None = None,
        local_memory: Any | None = None,
    ):
        super().__init__()
        self._market_provider = market_provider
        self._optimizer = optimizer or create_markowitz_optimizer()
        self._attribution = attribution or create_default_attribution_analysis()
        self._local_memory = local_memory

    def optimize_portfolio(
        self,
        request: OptimizationRequestDTO,
    ) -> OptimizationResultDTO:
        """Run portfolio optimization for given symbols."""
        assets = self._build_assets(request.symbols)

        result = self._optimizer.optimize(
            assets,
            method=request.method,
            target_return=request.target_return,
            risk_aversion=request.risk_aversion,
        )

        frontier = []
        if request.method != "black_litterman":
            frontier_points = self._optimizer.compute_frontier(assets, n_points=20)
            frontier = [
                {
                    "expected_return": p.expected_return,
                    "volatility": p.volatility,
                    "sharpe_ratio": p.sharpe_ratio,
                }
                for p in frontier_points
            ]

        return OptimizationResultDTO(
            optimal_weights=result.optimal_weights,
            expected_return=result.expected_return,
            volatility=result.volatility,
            sharpe_ratio=result.sharpe_ratio,
            method=result.method,
            frontier=frontier,
        )

    def remember_rebalance_lesson(
        self,
        *,
        symbol: str,
        weights_before: dict[str, float],
        weights_after: dict[str, float],
        description: str,
        score: float,
    ) -> dict[str, Any]:
        if self._local_memory is None:
            return {"ok": False, "error": "local_memory_unavailable"}
        entry = self._local_memory.remember_lesson(
            symbol=symbol,
            weights_before=weights_before,
            weights_after=weights_after,
            description=description,
            score=score,
        )
        return {"ok": True, "memory": entry.__dict__}

    def get_rebalance_lessons(self, symbol: str | None = None, top_k: int = 5) -> dict[str, Any]:
        if self._local_memory is None:
            return {"ok": False, "error": "local_memory_unavailable", "lessons": []}
        self._local_memory._load_all()
        lessons = [lesson.__dict__ for lesson in self._local_memory.recall_lessons(symbol=symbol, top_k=top_k)]
        return {"ok": True, "lessons": lessons, "memory": self._local_memory.get_memory_stats()}

    def get_portfolio_snapshot(
        self,
        symbols: list[str],
        holdings: dict[str, int],
        cash: float,
        benchmark_symbol: str = "000300",
    ) -> PortfolioSnapshotDTO:
        """Get current portfolio snapshot with positions."""
        quotes = self._market_provider.get_realtime_quotes(symbols=symbols, market=MarketCode.CN)
        quote_map = {q.code: q for q in quotes}

        positions = []
        total_value = cash
        position_values = {}

        for symbol, shares in holdings.items():
            q = quote_map.get(symbol)
            if q is None:
                continue
            value = float(shares) * float(q.price)
            position_values[symbol] = value
            total_value += value

        for symbol, shares in holdings.items():
            q = quote_map.get(symbol)
            if q is None:
                continue
            value = position_values[symbol]
            current_weight = value / total_value if total_value > 0 else 0
            prev_close = float(q.prev_close) if q.prev_close else float(q.price)
            return_pct = (float(q.price) - prev_close) / prev_close if prev_close > 0 else 0
            unrealized_pnl = value * return_pct

            positions.append(
                PortfolioPositionDTO(
                    symbol=symbol,
                    shares=shares,
                    current_price=float(q.price),
                    current_value=value,
                    target_weight=0.0,
                    current_weight=round(current_weight, 4),
                    weight_deviation=0.0,
                    unrealized_pnl=round(unrealized_pnl, 2),
                    return_pct=round(return_pct, 4),
                )
            )

        total_pnl = sum(p.unrealized_pnl for p in positions)
        total_return = total_pnl / total_value if total_value > 0 else 0

        benchmark_return = 0.0
        try:
            bm_history = self._market_provider.get_stock_history(
                benchmark_symbol, MarketCode.CN,
                (datetime.now().replace(month=1, day=1)).strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d"),
            )
            if len(bm_history) >= 2:
                bm_start = float(bm_history[0].get("close", 0))
                bm_end = float(bm_history[-1].get("close", 0))
                if bm_start > 0:
                    benchmark_return = (bm_end - bm_start) / bm_start
        except (OSError, RuntimeError, ValueError, TypeError, KeyError, AttributeError) as e:
            self.logger.error("Error fetching benchmark history: %s", e)

        return PortfolioSnapshotDTO(
            portfolio_id="default",
            total_value=round(total_value, 2),
            cash=round(cash, 2),
            positions=positions,
            total_return=round(total_return, 4),
            total_pnl=round(total_pnl, 2),
            benchmark_return=round(benchmark_return, 4),
            updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def check_rebalance_alerts(
        self,
        snapshot: PortfolioSnapshotDTO,
        target_weights: dict[str, float],
        threshold: float = 0.05,
    ) -> list[RebalanceAlertDTO]:
        """Check if any positions need rebalancing."""
        alerts = []
        for pos in snapshot.positions:
            target = target_weights.get(pos.symbol, 0.0)
            deviation = abs(pos.current_weight - target)

            if deviation > threshold:
                urgency = "high" if deviation > 0.15 else "medium" if deviation > 0.1 else "low"
                action = "减持" if pos.current_weight > target else "增持"
                alerts.append(
                    RebalanceAlertDTO(
                        symbol=pos.symbol,
                        current_weight=pos.current_weight,
                        target_weight=target,
                        deviation=round(deviation, 4),
                        action=action,
                        urgency=urgency,
                    )
                )

        return sorted(alerts, key=lambda a: a.deviation, reverse=True)

    def analyze_attribution(
        self,
        portfolio_return: float,
        benchmark_return: float,
        factor_exposures: dict[str, float],
        factor_returns: dict[str, float],
        alpha: float = 0.0,
    ) -> AttributionResultDTO:
        """Analyze portfolio attribution (Beta, Alpha, Style)."""
        result = self._attribution.decompose(
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            factor_exposures=factor_exposures,
            factor_returns=factor_returns,
            alpha=alpha,
        )
        return AttributionResultDTO(**result)

    def compute_risk_budget(
        self,
        symbols: list[str],
        holdings: dict[str, int],
    ) -> list[dict[str, Any]]:
        """Compute risk contribution per asset (CVaR/Vol contribution)."""
        quotes = self._market_provider.get_realtime_quotes(symbols=symbols, market=MarketCode.CN)
        quote_map = {q.code: q for q in quotes}

        risks = []
        total_var = 0.0
        values = {}

        for symbol, shares in holdings.items():
            q = quote_map.get(symbol)
            if q is None:
                continue
            value = float(shares) * float(q.price)
            vol = float(q.amplitude) / 100.0 if q.amplitude else 0.02
            var_contrib = value * vol
            values[symbol] = (value, var_contrib)
            total_var += var_contrib

        for symbol, (value, var) in values.items():
            pct = var / total_var if total_var > 0 else 0
            risks.append({
                "symbol": symbol,
                "var_contribution": round(var, 2),
                "weight": round(value / sum(v for v, _ in values.values()), 4),
                "marginal_var": round(pct, 4),
                "risk_contribution_pct": round(pct * 100, 2),
            })

        return sorted(risks, key=lambda r: r["var_contribution"], reverse=True)

    def _build_assets(self, symbols: list[str]) -> list[PortfolioAsset]:
        """Build portfolio assets from symbols using market data."""
        quotes = self._market_provider.get_realtime_quotes(symbols=symbols, market=MarketCode.CN)
        quote_map = {q.code: q for q in quotes}

        assets = []
        for symbol in symbols:
            q = quote_map.get(symbol)
            if q is None:
                assets.append(
                    PortfolioAsset(
                        symbol=symbol,
                        expected_return=0.0,
                        volatility=0.02,
                    )
                )
                continue

            prev_close = float(q.prev_close) if q.prev_close else float(q.price)
            ret_ytd = (float(q.price) - prev_close) / prev_close if prev_close > 0 else 0
            vol = float(q.amplitude) / 100.0 if q.amplitude else 0.02

            assets.append(
                PortfolioAsset(
                    symbol=symbol,
                    expected_return=ret_ytd,
                    volatility=max(vol, 0.01),
                )
            )

        return assets