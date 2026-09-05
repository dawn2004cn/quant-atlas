from __future__ import annotations

"""Strategy selection and backtest service with market sentiment awareness."""


import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.application.dto.strategy_dto import ScreeningCriteria
from app.core.base_service import BaseApplicationService
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.enums import MarketCode
from app.domain.ports import BacktestProvider, IndicatorProvider, MarketDataProvider, StrategyProvider
from app.domain.services.regime_manager import MarketRegimeManager

logger = logging.getLogger(__name__)
class StrategyApplicationService(BaseApplicationService):
    """Application service for selection and backtest use cases."""

    def __init__(
        self,
        strategy_provider: StrategyProvider,
        backtest_provider: BacktestProvider,
        market_provider: MarketDataProvider,
        indicator_provider: IndicatorProvider | None = None,
        news_provider=None,
        **kwargs,
    ):
        super().__init__()
        self._strategy_provider = strategy_provider
        self._backtest_provider = backtest_provider
        self._market_provider = market_provider
        self._indicator_provider = indicator_provider

    def list_strategies(self) -> list[dict[str, Any]]:
        """List available strategies through provider."""
        return self._strategy_provider.list_strategies()

    def get_strategy(self, name: str) -> dict[str, Any]:
        """Get a single strategy by name."""
        for s in self._strategy_provider.list_strategies():
            if s.get("name") == name or s.get("id") == name:
                return s
        return {"name": name, "error": "not_found"}

    def select_stocks(
        self,
        strategy_name: str | None = None,
        strategy: str | None = None,
        market: MarketCode = MarketCode.CN,
        top_n: int = 20,
        selector_type: str = "long",
        screening_criteria: dict[str, Any] | None = None,
        data_source: str = "legacy",
        enable_qlib: bool = False,
        model_id: str | None = None,
        horizon_days: int = 20,
    ) -> GenericResponseDTO[str, object]:
        """
        根据策略名（或 'smart' 智能情绪路由，或 'custom_criteria' 自定义筛选）选择股票

        Accepts both `strategy_name` (legacy) and `strategy` (alias) for compatibility
        with multiple callers.
        """
        # Support 'strategy' alias from route layer
        if strategy_name is None:
            strategy_name = strategy or "classic"
        effective_strategy = strategy_name
        sentiment_info = {}

        # 1. 自定义筛选模式
        if strategy_name.lower() == "custom_criteria" and screening_criteria:
            return self.custom_criteria_select_stocks(
                criteria=screening_criteria,
                market=market,
                top_n=top_n
            )

        # 2. 智能选股模式：根据情绪自动匹配策略
        if strategy_name.lower() in ["smart", "auto", "sentiment"]:
            # ... (Rest of existing smart logic)
            benchmark = market.benchmark
            index_history = self._market_provider.get_stock_history(benchmark, market, "2023-01-01", datetime.now().strftime("%Y-%m-%d"))
            if index_history:
                df_index = pd.DataFrame(index_history)
                df_index.rename(columns={"close": "Close"}, inplace=True)

                # 2. 分析大盘环境
                regime_mgr = MarketRegimeManager(df_index)
                regime = regime_mgr.get_current_regime()
                categories = regime_mgr.get_recommended_categories()

                # 3. 决定最终调用的策略标记
                effective_strategy = f"category:{','.join(categories)}"
                sentiment_info = {
                    "market_regime": regime,
                    "recommended_categories": categories,
                    "analysis_index": benchmark,
                }

        # 执行选股扫描 (Provider 基础选股)
        candidates = self._strategy_provider.select(effective_strategy, market, top_n, selector_type=selector_type)

        return {
            "strategy": strategy_name,
            "effective_strategy_group": effective_strategy,
            "market": market.value,
            "generated_at": datetime.now().isoformat(),
            "sentiment_analysis": sentiment_info,
            "candidates": candidates,
            "ok": True
        }

    def custom_criteria_select_stocks(
        self,
        criteria: dict[str, Any],
        market: MarketCode,
        top_n: int = 5,
        universe_limit: int = 200,
    ) -> GenericResponseDTO:
        """执行高度定制化的筛选：获取实时数据 -> 计算指标 -> 应用 Pydantic 逻辑规则"""

        # 1. 获取标的池 (默认成交额前 N)
        symbols = self._get_universe_symbols(market, limit=universe_limit)
        if not symbols:
            return {"ok": False, "error": "empty_universe", "candidates": []}

        # 2. 批量获取详情数据 (行情+基本面)
        stock_data = self._fetch_stock_data_batch(symbols, market)

        # 3. 注入情绪分析数据 (针对每一个标的，较慢，仅对前 N 进行)
        # 实际生产中这里应该有缓存
        # stock_data = self._enrich_with_sentiment(stock_data)

        # 4. 执行过滤逻辑
        conditions = criteria.get("conditions", [])
        logical_op = criteria.get("logical_operator", "AND")

        filtered = []
        for item in stock_data:
            match_results = []
            for cond in conditions:
                field = cond.get("field")
                op = cond.get("operator")
                target_val = cond.get("value")
                item_val = item.get(field)

                if item_val is not None:
                    match_results.append(self._compare(item_val, op, target_val))
                else:
                    match_results.append(False)

            is_match = all(match_results) if logical_op == "AND" else any(match_results)
            if is_match:
                filtered.append(item)

        # 5. 排序并裁剪
        results = sorted(filtered, key=lambda x: abs(x.get("change_pct", 0)), reverse=True)[:top_n]

        return {
            "ok": True,
            "strategy": "custom_criteria",
            "market": market.value,
            "total_matched": len(filtered),
            "candidates": results,
            "generated_at": datetime.now().isoformat()
        }

    def _enrich_with_sentiment(self, stock_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        try:
            from app.modules.system.services.helpers.news_provider_access import get_news_provider
            news_provider = get_news_provider()
        except Exception:
            return stock_data

        for item in stock_data:
            try:
                news = news_provider.get_stock_news(item["symbol"], MarketCode.CN)
                if not news:
                    item["sentiment_score"] = 0.5
                    item["news_positive_count"] = 0
                    item["news_negative_count"] = 0
                    item["news_neutral_count"] = 0
                    continue

                positive = sum(1 for n in news if n.sentiment > 0.6)
                negative = sum(1 for n in news if n.sentiment < 0.4)
                neutral = len(news) - positive - negative
                avg_sentiment = sum(n.sentiment for n in news) / len(news) if news else 0.5

                item["sentiment_score"] = round(avg_sentiment, 3)
                item["news_positive_count"] = positive
                item["news_negative_count"] = negative
                item["news_neutral_count"] = neutral
            except Exception:
                item["sentiment_score"] = 0.5
                item["news_positive_count"] = 0
                item["news_negative_count"] = 0
                item["news_neutral_count"] = 0
        return stock_data

    def _get_universe_symbols(self, market: MarketCode, limit: int) -> list[str]:
        try:
            quotes = self._market_provider.get_realtime_quotes(market=market)
            if market == MarketCode.CN:
                return [str(q.code).zfill(6) for q in quotes[:limit]]
            return [str(q.code) for q in quotes[:limit]]
        except Exception:
            return []

    def _fetch_stock_data_batch(self, symbols: list[str], market: MarketCode) -> list[dict[str, Any]]:
        data = []
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        for sym in symbols:
            try:
                history = self._market_provider.get_stock_history(sym, market, start, end)
                profile = self._market_provider.get_stock_profile(sym, market)

                indicators = {}
                if history and self._indicator_provider:
                    try:
                        indicators = self._indicator_provider.calculate(history)
                    except Exception as e:
                        logger.warning("strategy_service.py._fetch_stock_data_batch: %s", e)

                item = {
                    "symbol": sym,
                    "name": profile.get("name", ""),
                    "price": profile.get("price", 0) or 0,
                    "change_pct": profile.get("change_pct", 0) or 0,
                    "volume": profile.get("volume", 0) or 0,
                    "amount": profile.get("amount", 0) or 0,
                    "turnover": profile.get("turnover", 0) or 0,
                    "pe": profile.get("pe") or 0,
                    "pb": profile.get("pb") or 0,
                    "amplitude": profile.get("amplitude", 0) or 0,
                    "volume_ratio": profile.get("volume_ratio", 0) or 0,
                }
                item.update(indicators)
                data.append(item)
            except Exception:
                continue
        return data

    def _apply_criteria(self, stock_data: list[dict[str, Any]], criteria: ScreeningCriteria) -> list[dict[str, Any]]:
        if not criteria.rules:
            return stock_data

        results = []
        for item in stock_data:
            if self._match_rules(item, criteria.rules):
                results.append(item)

        return sorted(results, key=lambda x: abs(x.get("change_pct", 0)), reverse=True)

    def _match_rules(self, item: dict[str, Any], rules: list) -> bool:
        if not rules:
            return True

        for rule in rules:
            conditions = rule.get("conditions", [])
            if not conditions:
                continue

            rule_op = rule.get("operator", "AND")
            matched_conditions = []

            for cond in conditions:
                field = cond.get("field", "")
                op = cond.get("operator", ">")
                value = cond.get("value", 0)

                item_val = item.get(field, 0) or 0
                if item_val is None:
                    item_val = 0

                matched = self._compare(item_val, op, value)
                matched_conditions.append(matched)

            if rule_op == "AND":
                if not all(matched_conditions):
                    return False
            elif rule_op == "OR":
                if not any(matched_conditions):
                    return False
            elif rule_op == "NOT":
                if matched_conditions and matched_conditions[0]:
                    return False

        return True

    def _compare(self, item_val: float, op: str, threshold: float) -> bool:
        op_map = {
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "=": lambda a, b: abs(a - b) < 0.001,
            "!=": lambda a, b: abs(a - b) >= 0.001,
        }
        cmp_fn = op_map.get(op, op_map[">"])
        return cmp_fn(item_val, threshold)

    def backtest(
        self,
        symbol: str,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
        commission_rate: float | None = None,
        slippage_bps: float | None = None,
    ) -> GenericResponseDTO:
        """Run backtest for a symbol with given strategy."""
        if self._backtest_provider is None:
            return {"error": "backtest provider not available"}
        try:
            return self._backtest_provider.backtest(
                symbol=symbol,
                strategy=strategy_name,
                start=start,
                end=end,
                initial_capital=initial_capital,
                commission_rate=commission_rate,
                slippage_bps=slippage_bps,
            )
        except Exception as e:
            self.logger.error(f"Backtest failed: {e}")
            return {"error": f"backtest failed: {str(e)}"}
