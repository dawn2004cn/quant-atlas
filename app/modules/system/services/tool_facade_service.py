from __future__ import annotations
"""Tool facade service - delegates to self-registering capabilities."""


from typing import Any

from app.domain.enums import MarketCode
from app.domain.ports import ToolFacadePort
from app.domain.ports import MarketDataProvider
from app.domain.ports.news_archive_port import NewsArchiveRepository
from app.domain.ports.cn_fundamentals_port import CnFundamentalsPort
from app.modules.system.services.helpers.cn_fundamentals_access import get_cn_fundamentals_port
from app.modules.market_data.services.stock_service import StockApplicationService
from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService
from app.infrastructure.capabilities.registry import CapabilityRegistry


_tool_facade_service_instance = None


def get_tool_facade_service() -> ToolFacadeService:
    """Get or create the global ToolFacadeService instance."""
    global _tool_facade_service_instance
    if _tool_facade_service_instance is None:
        from app.modules.system.services.helpers.market_data_provider import get_market_data_provider
        from app.modules.system.services.helpers.cn_fundamentals_access import get_cn_fundamentals_port
        from app.modules.system.services.helpers.strategy_providers_access import (
            create_backtest_provider,
            create_strategy_provider,
        )
        from app.modules.market_data.services.stock_service import StockApplicationService
        from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService

        market_provider = get_market_data_provider()
        stock_service = StockApplicationService(market_provider=market_provider)
        strategy_service = StrategyApplicationService(
            strategy_provider=create_strategy_provider(market_provider),
            backtest_provider=create_backtest_provider(),
            market_provider=market_provider,
        )

        from app.config import get_settings
        from app.infrastructure.repositories.common.deps import create_news_archive_repository

        settings = get_settings()
        archive_repo = create_news_archive_repository(settings)

        _tool_facade_service_instance = ToolFacadeService(
            market_provider=market_provider,
            stock_service=stock_service,
            archive=archive_repo,
            fundamental_provider=get_cn_fundamentals_port(),
            strategy_service=strategy_service,
        )
    return _tool_facade_service_instance


class ToolFacadeService(ToolFacadePort):
    """Unified tool facade - delegates to self-registering capabilities.

    The :class:`CapabilityRegistry` discovers capabilities via the
    ``@capability`` decorator.  Adding a new tool no longer requires
    editing this class â?just create a new capability class with the
    decorator in ``app/infrastructure/capabilities/``.
    """

    def __init__(
        self,
        market_provider: MarketDataProvider,
        stock_service: StockApplicationService,
        archive: NewsArchiveRepository | None = None,
        fundamental_provider: CnFundamentalsPort | None = None,
        strategy_service: StrategyApplicationService | None = None,
    ) -> None:
        # Keep direct references for backward compatibility.
        self._marketProvider = market_provider
        self._stockService = stock_service
        self._archive = archive
        self._fundamentalProvider = fundamental_provider or get_cn_fundamentals_port()
        self._strategyService = strategy_service

        self._registry = CapabilityRegistry(
            market_provider=market_provider,
            stock_service=stock_service,
            archive=archive,
            fundamental_provider=fundamental_provider or get_cn_fundamentals_port(),
            strategy_service=strategy_service,
        )

    # ââ capability-aware public interface âââââââââââââââââââââââââââââââââ

    def list_capabilities(self) -> list[str]:
        """Return all registered capability names."""
        return self._registry.list_capabilities()

    def execute_capability(self, name: str, **kwargs: Any) -> tuple[Any, str]:
        """Execute a named capability with the given keyword arguments."""
        return self._registry.execute(name, **kwargs)

    # ââ backward-compatible wrapper methods âââââââââââââââââââââââââââââââ

    def fetch_bars(
        self,
        symbol: str,
        market: MarketCode,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> tuple[list[dict], str]:
        """Return (bars, evidence_note)."""
        return self._registry.execute(
            "fetch_bars",
            symbol=symbol,
            market=market,
            period=period,
            interval=interval,
        )

    def fetch_profile(self, symbol: str, market: MarketCode) -> tuple[dict | None, str]:
        """Lightweight profile probe for ticker validation."""
        return self._registry.execute("fetch_profile", symbol=symbol, market=market)

    def cn_financial_bundle(self, symbol: str) -> Any:
        """Return financial bundle for symbol."""
        return self._registry.execute("cn_financial_bundle", symbol=symbol)[0]

    def cn_research_reports(
        self, symbol: str, limit: int = 30
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return research reports for symbol."""
        return self._registry.execute("cn_research_reports", symbol=symbol, limit=limit)

    def news_bundle(
        self,
        symbol: str,
        market: MarketCode,
        *,
        force_refresh: bool = False,
        cache_max_age_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Return bundled news with archive."""
        return self._registry.execute(
            "news_bundle",
            symbol=symbol,
            market=market,
            force_refresh=force_refresh,
            cache_max_age_hours=cache_max_age_hours,
        )[0]

    def run_backtest(
        self,
        *,
        strategy_name: str,
        ticker: str,
        market: MarketCode,
        params: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        """Run backtest and return (result, note)."""
        return self._registry.execute(
            "run_backtest",
            strategy_name=strategy_name,
            ticker=ticker,
            market=market,
            params=params,
        )

    def run_selector(
        self,
        *,
        model_name: str,
        market: MarketCode,
        criteria: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        """Run stock selection and return (result, note)."""
        return self._registry.execute(
            "run_selector",
            model_name=model_name,
            market=market,
            criteria=criteria,
        )

    # ââ tool facade wrapper methods ââââââââââââââââââââââââââââââââââââââââ

    def stock_selection(
        self,
        *,
        model_name: str,
        criteria: dict[str, Any] | None = None,
        screening_criteria: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Stock selection wrapper for tools."""
        merged_criteria = criteria or screening_criteria or {}
        result, _ = self.run_selector(
            model_name=model_name,
            market=MarketCode.CN,
            criteria=merged_criteria,
        )
        return result

    def get_financial_data(
        self,
        ticker: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Get financial data wrapper for tools."""
        bundle = self.cn_financial_bundle(ticker)
        return bundle or {}

    def get_kline_chart_url(self, ticker: str, *, period: str = "1y") -> str:
        """Generate K-line chart URL for tools."""
        return f"/static/charts/{ticker}_{period}.png"

    def get_chip_distribution(self, ticker: str) -> dict[str, Any]:
        """Get chip distribution data for tools (Rust-accelerated)."""
        try:
            from app.infrastructure.compute.native_compute import calculate_chip_distribution
            # Get historical price+volume data
            from app.modules.system.services.tools.tool_facade_service import get_tool_facade_service
            svc = get_tool_facade_service()
            history = getattr(svc, "_fetch_stock_history", None) or getattr(self, "_fetch_stock_history", None)
            if history:
                kline = history(ticker, period="1y")
            else:
                kline = []
            if kline and len(kline) >= 20:
                prices = [float(k["close"]) for k in kline if isinstance(k, dict) and k.get("close")]
                volumes = [float(k["volume"]) for k in kline if isinstance(k, dict) and k.get("volume")]
                total_shares = float(kline[-1].get("total_shares", 0)) if isinstance(kline[-1], dict) else 0
                dist = calculate_chip_distribution(prices, volumes, total_shares or 1.0)
                return {"ticker": ticker, **dist}
            return {"ticker": ticker, "profit_ratio": 0.0, "avg_cost": 0.0, "concentration_90": 0.0, "concentration_70": 0.0}
        except Exception as e:
            return {"ticker": ticker, "profit_ratio": 0.0, "avg_cost": 0.0, "concentration_90": 0.0, "concentration_70": 0.0, "error": str(e)}

    def get_longhu_data(self, ticker: str, *, max_rows: int = 15) -> list[dict[str, Any]]:
        """Get longhu (dragon-tiger) data for tools."""
        return []
