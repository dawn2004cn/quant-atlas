from __future__ import annotations

"""Strategy and backtest adapters using new app/core and app/models."""


from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

from app.core.logger import get_logger

from ...core.engine import HolyGrailEnsembleEngine
from ...core.factory import StrategyFactory
from ...core.risk_controls import (
    RiskControlParams,
)
from ...domain.entities import BacktestReport, StrategyConfig
from ...domain.enums import MarketCode
from ...domain.ports import BacktestProvider, StrategyProvider
from ...models import ALL_STRATEGIES
from .backtest_engine import BacktestEngine

logger = get_logger(__name__)


class DefaultStrategyProvider(StrategyProvider):
    """Standard strategy provider using the HolyGrailEnsembleEngine."""

    def __init__(self, cache: Any | None = None, market_provider: Any | None = None):
        from .market_data import MultiSourceMarketProvider
        self._engine = HolyGrailEnsembleEngine()
        self._all_models = ALL_STRATEGIES
        self._cache = cache
        self._market = market_provider or MultiSourceMarketProvider()

    def select(self, strategy_name: str, market: MarketCode, top_n: int, selector_type: str = "long") -> list[dict]:
        """全市场扫描选股"""
        import time
        t0 = time.monotonic()
        target_models = []

        if strategy_name.startswith("horizon:"):
            target_horizon = strategy_name.replace("horizon:", "").strip()
            target_models = [m for m in self._all_models if target_horizon in m.horizon_tags()]
        elif strategy_name.startswith("category:"):
            allowed_categories = strategy_name.replace("category:", "").split(",")
            target_models = [m for m in self._all_models if m.category in allowed_categories]
        elif strategy_name.lower() in ["all", "resonance", "smart"]:
            target_models = self._all_models
        else:
            target_models = [
                m for m in self._all_models
                if strategy_name.lower() in m.name.lower() or strategy_name.lower() in m.__class__.__name__.lower()
            ]

        if not target_models:
            target_models = self._all_models

        self._engine.load_models(target_models)
        t1 = time.monotonic()
        stock_data_dict = self._prepare_scan_data(market=market, limit=5000)
        t2 = time.monotonic()
        report_df = self._engine.run_market_scan(stock_data_dict)
        t3 = time.monotonic()

        if report_df.empty:
            return []

        results = []
        for _, row in report_df.head(top_n).iterrows():
            results.append({
                "code": row["代码"],
                "name": row.get("名称", row["代码"]),
                "price": row["最新收盘价"],
                "score": row["共振得分"],
                "reason": row["主力买入逻辑"],
                "rating": "A" if row["共振得分"] >= 80 else "B",
                "buy_signals": row["主力买入逻辑"].split(" | ")
            })

        total_ms = (time.monotonic() - t0) * 1000
        logger.info(
            "[%s] 挂载 %s 模型 | 准备 %sms | 扫描 %sms | 总计 %sms",
            selector_type,
            len(target_models),
            int((t2 - t1) * 1000),
            int((t3 - t2) * 1000),
            int(total_ms),
        )
        return results

    def _prepare_scan_data(self, market: MarketCode, limit: int = 500) -> dict[str, pd.DataFrame]:
        """从缓存或行情API加载全市场股票数据用于扫描"""
        data_dict = {}
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=220)).strftime("%Y-%m-%d")

            if market == MarketCode.CN:
                from ..database.stock_cache_db import StockCache
                cache = self._cache or StockCache()
                stocks = cache.get_all_stocks(max_age_minutes=1440)
                for s in stocks[:limit]:
                    code = s["code"]
                    history = cache.get_stock_history(code, start_date, end_date)
                    if history and len(history) > 30:
                        df = self._history_to_df(history)
                        data_dict[code] = df
            else:
                quotes = self._market.get_realtime_quotes(None, market)
                for q in quotes[:limit]:
                    code = q.code if hasattr(q, "code") else str(q.get("code", q.get("symbol", "")))
                    name = q.name if hasattr(q, "name") else str(q.get("name", ""))
                    history = self._market.get_stock_history(code, market, start_date, end_date)
                    if history and len(history) > 30:
                        df = self._history_to_df(history)
                        data_dict[code] = df
                        data_dict[code].attrs["name"] = name
        except Exception as e:
            logger.warning("Prepare scan data failed [%s]: %s", market.value, e, exc_info=True)

        return data_dict

    def _history_to_df(self, history: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert history list to DataFrame with standard column names."""
        df = pd.DataFrame(history)
        col_map = {c.lower(): c for c in df.columns}
        df.rename(columns={
            col_map.get("date", "date"): "Date",
            col_map.get("open", "open"): "Open",
            col_map.get("high", "high"): "High",
            col_map.get("low", "low"): "Low",
            col_map.get("close", "close"): "Close",
            col_map.get("volume", "volume"): "Volume"
        }, inplace=True)
        return df

    def list_strategies(self) -> list[dict[str, Any]]:
        return [{"name": m.name, "category": m.category} for m in self._all_models]

    def generate_signals(self, symbol: str, market: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
        results = self.select(params.get("strategy", "all"), market, params.get("top_n", 10))
        return results


class DefaultBacktestProvider(BacktestProvider):
    """Standard backtest provider using validated strategy models."""
    _risk = RiskControlParams()

    def backtest(
        self,
        symbol: str,
        strategy: str,
        start: str,
        end: str,
        initial_capital: float = 100000.0,
        commission_rate: float | None = None,
        slippage_bps: float | None = None,
    ) -> dict[str, Any]:
        try:
            report = self.run(
                symbol,
                strategy,
                start,
                end,
                initial_capital,
                commission_rate=commission_rate,
                slippage_bps=slippage_bps,
            )
            if hasattr(report, 'to_dict'):
                return report.to_dict()
            return {"status": "completed", "report": str(report)}
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"error": str(e), "status": "failed"}

    def run(
        self,
        symbol: str,
        strategy_name: str,
        start: str,
        end: str,
        initial_capital: float,
        commission_rate: float | None = None,
        slippage_bps: float | None = None,
    ) -> BacktestReport:
        self._commission_rate = commission_rate
        self._slippage_bps = slippage_bps
        sid = (strategy_name or "").strip()
        strategy = StrategyFactory.create(StrategyConfig(strategy_id=sid, parameters={}))
        if strategy is None:
            strategy = next(
                (
                    m
                    for m in ALL_STRATEGIES
                    if sid.lower() in m.name.lower() or sid.lower() in m.__class__.__name__.lower()
                ),
                ALL_STRATEGIES[0],
            )

        # 支持组合回测：symbol 允许 "600519,000001" 或空格分隔
        raw = (symbol or "").replace("，", ",")
        syms = [s.strip() for s in raw.replace(" ", ",").split(",") if s.strip()]
        if not syms:
            return self._empty_report(symbol, strategy_name, start, end, initial_capital)

        from .market_data import MultiSourceMarketProvider

        provider = MultiSourceMarketProvider()
        dfs: dict[str, pd.DataFrame] = {}
        for sym in syms[:60]:
            history = provider.get_stock_history(sym, MarketCode.CN, start, end)
            if not history:
                continue

            # First, deduplicate any duplicate keys in history records
            deduped = []
            for rec in history:
                # Keep only lowercase version of each key
                seen = set()
                new_rec = {}
                for k, v in rec.items():
                    k_lower = k.lower()
                    if k_lower not in seen:
                        new_rec[k_lower if k_lower in ('date','open','high','low','close','volume','amount') else k] = v
                        seen.add(k_lower)
                deduped.append(new_rec)

            df = pd.DataFrame(deduped)
            rename_map = {
                'date': 'Date', 'open': 'Open', 'high': 'High',
                'low': 'Low', 'close': 'Close', 'volume': 'Volume'
            }
            existing_rename = {k: v for k, v in rename_map.items() if k in df.columns}
            if existing_rename:
                df = df.rename(columns=existing_rename)
            need = {"Date", "Open", "High", "Low", "Close", "Volume"}
            if not need.issubset(set(df.columns)) or df.empty:
                continue
            dfs[sym] = df

        if not dfs:
            return self._empty_report(symbol, strategy_name, start, end, initial_capital)

        # 单标的：保持原行为（直接使用策略信号序列）
        if len(dfs) == 1:
            only_sym, df0 = next(iter(dfs.items()))
            sig_df = strategy.generate_signals(df0)
            report = self._simulate_backtest(sig_df, initial_capital)
            sym_out = only_sym
        else:
            report = self._simulate_portfolio_backtest(dfs, strategy, initial_capital)
            sym_out = ",".join(dfs.keys())

        return BacktestReport(
            strategy=strategy.name,
            symbol=sym_out,
            period={"start": start, "end": end},
            metrics=report["metrics"],
            trades=report["trades"],
        )

    def _can_trade_cn(self, df: pd.DataFrame, i: int, *, side: str, limit_thr: float) -> tuple[bool, str]:
        """A 股日频近似：停牌/无量、一字板、涨跌停约束。"""
        from .cn_backtest_rules import can_trade_cn_bar

        return can_trade_cn_bar(df, i, side=side, limit_thr=limit_thr)

    @staticmethod
    def _normalize_bt_trade_date(raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            s = raw.strip().replace("/", "-")
            return s[:10] if len(s) >= 10 else s
        ts = pd.Timestamp(raw)
        if pd.isna(ts):
            return ""
        return ts.strftime("%Y-%m-%d")

    @staticmethod
    def _score_from_sentiment_row(row: dict[str, Any]) -> float:
        up = float(row.get("up_count") or 0)
        total = float(row.get("total_count") or 0)
        if total <= 0:
            return 50.0
        return max(0.0, min(100.0, round((up / total) * 100.0, 2)))

    def _cross_section_breadth_score(self, df_by_sym: dict[str, pd.DataFrame], t: int) -> float:
        """多标的：当日相对昨收的上涨家数占比 → 0~100。"""
        if t <= 0:
            return 50.0
        up = tot = 0
        for _sym, x in df_by_sym.items():
            if t >= len(x):
                continue
            try:
                c = float(pd.to_numeric(x["Close"].iloc[t], errors="coerce"))
                p = float(pd.to_numeric(x["Close"].iloc[t - 1], errors="coerce"))
            except Exception:
                continue
            if not (np.isfinite(c) and np.isfinite(p)) or p <= 0:
                continue
            tot += 1
            if c > p:
                up += 1
        if tot <= 0:
            return 50.0
        return max(0.0, min(100.0, round(100.0 * up / tot, 2)))

    def _single_symbol_direction_score(self, df: pd.DataFrame, i: int) -> float:
        """单标的：无全市场日数据时用自身涨跌作粗近似（非全市场 breadth）。"""
        if i <= 0 or i >= len(df):
            return 50.0
        try:
            c = float(pd.to_numeric(df["Close"].iloc[i], errors="coerce"))
            p = float(pd.to_numeric(df["Close"].iloc[i - 1], errors="coerce"))
        except Exception:
            return 50.0
        if not (np.isfinite(c) and np.isfinite(p)) or p <= 0:
            return 50.0
        if c > p:
            return 100.0
        if c < p:
            return 0.0
        return 50.0

    def _cn_sentiment_for_trade_date(
        self,
        trade_date: str,
        *,
        df_by_sym: dict[str, pd.DataFrame] | None,
        bar_index: int,
    ) -> float:
        """回测用：优先 ``market_sentiment_daily``；否则多标的横截面；再否则单标的涨跌；最后 50。"""
        d = (trade_date or "").strip()[:10]
        if not d:
            return 50.0
        try:
            from ..database.stock_cache_db import StockCache

            row = StockCache.default().get_sentiment_for_trade_date("CN", d)
            if row and int(row.get("total_count") or 0) > 0:
                return self._score_from_sentiment_row(row)
        except Exception as e:
            logger.warning("strategies.py._cn_sentiment_for_trade_date: %s", e)
        if df_by_sym and len(df_by_sym) >= 2 and bar_index > 0:
            return self._cross_section_breadth_score(df_by_sym, bar_index)
        if df_by_sym and len(df_by_sym) == 1 and bar_index > 0:
            only = next(iter(df_by_sym.values()))
            return self._single_symbol_direction_score(only, bar_index)
        return 50.0

    def _latest_cn_sentiment_score(self) -> float:
        """市场情绪分：优先读缓存/落库的 breadth（上涨家数占比），不可用则回退 50。"""
        try:
            from ..database.stock_cache_db import StockCache

            cache = StockCache.default()
            row = cache.get_latest_sentiment("CN") or {}
            up = float(row.get("up_count") or 0)
            total = float(row.get("total_count") or 0)
            if total <= 0:
                return 50.0
            return max(0.0, min(100.0, round((up / total) * 100.0, 2)))
        except Exception:
            return 50.0

    def _simulate_portfolio_backtest(self, dfs: dict[str, pd.DataFrame], strategy: Any, initial_capital: float) -> dict:
        """多标的组合回测 - 委托给BacktestEngine."""
        engine = BacktestEngine(
            commission_rate=getattr(self, "_commission_rate", None),
            slippage_bps=getattr(self, "_slippage_bps", None),
        )
        return engine.simulate_portfolio_backtest(dfs, strategy, initial_capital)

    def _simulate_backtest(self, df: pd.DataFrame, initial_capital: float) -> dict:
        """单标的回测 - 委托给BacktestEngine."""
        from ...models import ALL_STRATEGIES
        strategy = ALL_STRATEGIES[0] if ALL_STRATEGIES else None
        engine = BacktestEngine(
            commission_rate=getattr(self, "_commission_rate", None),
            slippage_bps=getattr(self, "_slippage_bps", None),
        )
        return engine.simulate_single_backtest(df, strategy, initial_capital)

    def _empty_report(self, symbol, strategy, start, end, capital):
        return BacktestReport(
            strategy=strategy, symbol=symbol, period={"start": start, "end": end},
            metrics={"final_value": capital, "total_return": 0, "annual_return": 0, "max_drawdown": 0, "sharpe_ratio": 0, "stock_data": {}},
            trades=[]
        )
