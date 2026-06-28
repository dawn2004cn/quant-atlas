from __future__ import annotations

"""Backtest Engine - 回测核心引擎模块.

Deprecated: This engine is preserved for compatibility. New production backtests
should use CompositeEngine (app/infrastructure/agent/backtest/engines/)
which provides market-specific T+1, limit-up/down, and shift(1) correct semantics.

See: docs/审计白皮书.md — Phase 2 回测统一
"""


import warnings
from datetime import date
from typing import Any

import pandas as pd

from ...core.logger import get_logger
from ...core.risk_controls import (
    compute_atr,
    compute_liquidity_filters,
    load_default_position_sizing_params,
    load_default_risk_params,
    load_default_trade_cost_params,
    round_shares_for_market,
)
from ..compute.native_compute import (
    calculate_annual_return,
    calculate_max_drawdown,
    calculate_sharpe_ratio,
)
from .backtest_dividends import dividend_cash_for_bar
from .cn_backtest_rules import can_trade_cn_on_date, is_cn_symbol

logger = get_logger(__name__)


def _ohlcv_series_payload(df: pd.DataFrame) -> dict[str, Any]:
    """Build chart-friendly date/close arrays from a history frame."""
    work = df.copy()
    if "Date" not in work.columns:
        work = work.reset_index()
    dates = pd.to_datetime(work["Date"], errors="coerce")
    closes = pd.to_numeric(work.get("Close"), errors="coerce")
    mask = dates.notna() & closes.notna()
    dates = dates[mask]
    closes = closes[mask]
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in dates.dt.date],
        "closes": [float(c) for c in closes.tolist()],
    }


class BacktestEngine:
    """回测引擎 - 负责组合和单标的回测逻辑.

    Deprecated: Use CompositeEngine for production backtests.
    See module-level docstring for migration details.
    """

    def __init__(self):
        warnings.warn(
            "BacktestEngine is deprecated. Use CompositeEngine "
            "(app/infrastructure/agent/backtest/engines/) for production backtests.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.risk = load_default_risk_params()
        self.costs = load_default_trade_cost_params()
        self.sizing = load_default_position_sizing_params()

    @staticmethod
    def _slippage_price(price: float, side: str, slippage_bps: float) -> float:
        """Apply one-sided slippage (bps) to execution price."""
        mult = slippage_bps / 10000.0
        if side == "buy":
            return price * (1.0 + mult)
        if side == "sell":
            return price * (1.0 - mult)
        return price

    @staticmethod
    def _buy_costs(notional: float, costs: Any) -> float:
        return notional * (costs.commission_rate + costs.transfer_fee)

    @staticmethod
    def _sell_costs(notional: float, costs: Any) -> float:
        return notional * (
            costs.commission_rate + costs.stamp_tax_rate + costs.transfer_fee
        )

    @staticmethod
    def _apply_dividends_for_day(
        df: pd.DataFrame,
        dt: Any,
        positions: dict,
        cash: float,
        *,
        apply_dividends: bool,
        trades: list | None = None,
        symbol: str | None = None,
    ) -> float:
        """Credit cash dividends for held shares (unadjusted bars with Dividend column)."""
        if not apply_dividends or not positions or dt not in df.index:
            return cash
        bar = df.loc[dt]
        for pos in positions.values():
            shares = float(pos.get("shares", 0))
            amount = dividend_cash_for_bar(bar, shares)
            if amount <= 0:
                continue
            cash += amount
            if trades is not None:
                trades.append(
                    {
                        "date": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
                        "symbol": symbol,
                        "action": "dividend",
                        "amount": round(amount, 4),
                        "shares": shares,
                    }
                )
        return cash

    @staticmethod
    def _resolve_bar_date(df: pd.DataFrame, dt: Any) -> Any:
        if dt in df.index:
            return dt
        if isinstance(dt, str):
            try:
                from datetime import date as date_cls

                parsed = date_cls.fromisoformat(dt)
                if parsed in df.index:
                    return parsed
            except ValueError:
                logger.debug("Date parse fallthrough for dt=%s", dt)
        return None

    def simulate_portfolio_backtest(
        self,
        dfs: dict[str, pd.DataFrame],
        strategy: Any,
        initial_capital: float,
    ) -> dict:
        """多标的组合回测."""
        risk = load_default_risk_params()
        costs = load_default_trade_cost_params()
        sizing = load_default_position_sizing_params()

        dates_sets = []
        for df in dfs.values():
            dates = pd.to_datetime(df["Date"], errors="coerce")
            dates_sets.append(set([d.date().isoformat() for d in dates.dropna().tolist()]))
        common = set.intersection(*dates_sets) if dates_sets else set()
        cal = sorted(common)
        if not cal:
            return self._empty_result(initial_capital)

        sig_map, filt_map, atr_map, df_by_sym = self._prepare_signals(dfs)

        positions = {}
        cash = initial_capital
        equity_curve = []
        trades = []
        daily_pnl = {d: 0.0 for d in cal}
        dividend_income = 0.0

        max_pos = getattr(strategy, "max_positions", 5)

        for i, dt in enumerate(cal):
            dt_str = dt.isoformat() if isinstance(dt, date) else str(dt)

            for sym, pos in list(positions.items()):
                if sym not in df_by_sym:
                    continue
                bar_dt = self._resolve_bar_date(df_by_sym[sym], dt_str)
                if bar_dt is None:
                    continue
                before = cash
                cash = self._apply_dividends_for_day(
                    df_by_sym[sym],
                    bar_dt,
                    {sym: pos},
                    cash,
                    apply_dividends=costs.apply_cash_dividends,
                    trades=trades,
                    symbol=sym,
                )
                dividend_income += cash - before

            self._process_exits(dt_str, positions, df_by_sym, atr_map, risk, costs, trades, daily_pnl)

            self._process_entries(
                dt_str, i, cal, positions, df_by_sym, sig_map, filt_map, atr_map,
                cash, max_pos, risk, sizing, costs, trades, daily_pnl
            )

            pos_value = sum(
                self._calc_pos_value(positions[sym], df_by_sym[sym], dt_str)
                for sym in positions
            )
            equity_curve.append({"date": dt_str, "value": cash + pos_value})
            daily_pnl[dt_str] = pos_value - sum(
                self._calc_pos_value(positions[sym], df_by_sym[sym], cal[i-1].isoformat() if i > 0 else dt_str)
                for sym in positions
            )

        cash + sum(
            self._calc_pos_value(positions[sym], df_by_sym[sym], cal[-1].isoformat() if cal else "")
            for sym in positions
        )

        metrics = self._compute_metrics(equity_curve, initial_capital, trades)
        metrics["dividend_income"] = round(dividend_income, 4)
        first_sym = sorted(dfs.keys())[0] if dfs else None
        if first_sym and first_sym in dfs:
            metrics["stock_data"] = _ohlcv_series_payload(dfs[first_sym])
        else:
            metrics["stock_data"] = {}
        metrics["equity_curve"] = equity_curve

        return {"metrics": metrics, "trades": trades, "stock_data": metrics["stock_data"], "equity_curve": equity_curve}

    def simulate_single_backtest(
        self,
        df: pd.DataFrame,
        strategy: Any,
        initial_capital: float,
    ) -> dict:
        """单标的回测."""
        risk = load_default_risk_params()
        costs = load_default_trade_cost_params()
        sizing = load_default_position_sizing_params()

        if df.empty or "Date" not in df.columns or "Close" not in df.columns:
            return self._empty_result(initial_capital)

        stock_df = df.copy()
        dates = pd.to_datetime(stock_df["Date"]).dt.date.unique()
        cal = sorted(dates)
        if not cal:
            return self._empty_result(initial_capital)

        df = df.set_index("Date")
        df.index = pd.to_datetime(df.index).date

        atr = compute_atr(df, window=14)
        compute_liquidity_filters(df)

        positions = {}
        cash = initial_capital
        trades = []
        equity_curve = []
        daily_pnl = {}
        dividend_income = 0.0

        for i, dt in enumerate(cal):
            dt_str = dt.isoformat()
            close = df.loc[dt, "Close"] if dt in df.index else 0

            before = cash
            cash = self._apply_dividends_for_day(
                df,
                dt,
                positions,
                cash,
                apply_dividends=costs.apply_cash_dividends,
                trades=trades,
            )
            dividend_income += cash - before

            for entry_dt, pos in list(positions.items()):
                pnl = (close - pos["entry_price"]) * pos["shares"]
                daily_pnl[dt_str] = pnl
                pos["current_price"] = close

                if self._should_stop_loss(dt, df, i, atr, risk) or self._should_take_profit(dt, df, i, risk):
                    if not self._cn_trade_allowed(risk, "", df, dt, "SELL"):
                        continue
                    exec_price = self._slippage_price(close, "sell", costs.slippage_bps)
                    proceeds = exec_price * pos["shares"]
                    costs_total = self._sell_costs(proceeds, costs)
                    cash += proceeds - costs_total
                    trades.append({"date": dt_str, "action": "SELL", "price": exec_price, "pnl": pnl})
                    del positions[entry_dt]
            else:
                daily_pnl[dt_str] = 0

            if len(positions) == 0 and i < len(cal) - 30:
                sig_df = strategy.generate_signals(df.iloc[:i+1])
                if isinstance(sig_df, pd.DataFrame) and len(sig_df) > 0:
                    last_signal = int(sig_df["Signal"].iloc[-1]) if "Signal" in sig_df.columns else 0
                    if last_signal == 1 and self._cn_trade_allowed(risk, "", df, dt, "BUY"):
                        exec_price = self._slippage_price(close, "buy", costs.slippage_bps)
                        shares = self._calc_shares(cash, exec_price, sizing)
                        if shares > 0:
                            notional = exec_price * shares
                            costs_total = self._buy_costs(notional, costs)
                            if cash >= notional + costs_total:
                                cash -= notional + costs_total
                                positions[dt] = {
                                    "entry_date": dt_str,
                                    "entry_price": exec_price,
                                    "shares": shares,
                                    "current_price": close,
                                }
                                trades.append({"date": dt_str, "action": "BUY", "price": exec_price, "quantity": shares, "cost": notional + costs_total})

            pos_value = sum(p["shares"] * p["current_price"] for p in positions.values())
            equity_curve.append({"date": dt_str, "value": cash + pos_value})

        cash + sum(
            p["shares"] * p["current_price"] for p in positions.values()
        )

        metrics = self._compute_metrics(equity_curve, initial_capital, trades)
        metrics["dividend_income"] = round(dividend_income, 4)
        stock_data = _ohlcv_series_payload(stock_df)
        metrics["stock_data"] = stock_data
        metrics["equity_curve"] = equity_curve
        return {
            "metrics": metrics,
            "trades": trades,
            "stock_data": stock_data,
            "equity_curve": equity_curve,
        }

    def _prepare_signals(self, dfs: dict[str, pd.DataFrame]) -> tuple:
        sig_map, filt_map, atr_map, df_by_sym = {}, {}, {}, {}
        for sym, df in dfs.items():
            df_copy = df.copy()
            dates = pd.to_datetime(df_copy["Date"]).dt.date
            df_copy["Date"] = dates
            df_by_sym[sym] = df_copy.set_index("Date")
            if hasattr(df_by_sym[sym], "signal"):
                sig_map[sym] = df_by_sym[sym]["signal"].fillna(0)
            else:
                sig_map[sym] = pd.Series(0, index=df_by_sym[sym].index)
            filt_map[sym] = pd.Series(True, index=df_by_sym[sym].index)
            atr_map[sym] = compute_atr(df_by_sym[sym], window=14)
        return sig_map, filt_map, atr_map, df_by_sym

    def _cn_trade_allowed(
        self,
        risk: Any,
        sym: str,
        df: pd.DataFrame,
        dt: Any,
        side: str,
    ) -> bool:
        if not getattr(risk, "apply_cn_price_limits", True):
            return True
        if sym and not is_cn_symbol(sym):
            return True
        bar_dt = dt
        if isinstance(dt, str):
            bar_dt = self._resolve_bar_date(df, dt)
        if bar_dt is None or bar_dt not in df.index:
            return True
        ok, _reason = can_trade_cn_on_date(
            df,
            bar_dt,
            side=side,
            limit_thr=self.sizing.limit_threshold,
            symbol=sym or None,
        )
        return ok

    def _process_exits(self, dt: str, positions: dict, df_by_sym: dict, atr_map: dict, risk: dict, costs: Any, trades: list, daily_pnl: dict):
        to_close = []
        for sym, pos in positions.items():
            if sym not in df_by_sym:
                continue
            df = df_by_sym[sym]
            if dt not in df.index:
                continue
            close = df.loc[dt, "Close"]
            entry_price = pos["entry_price"]
            pnl = (close - entry_price) * pos["shares"]
            daily_pnl[dt] = daily_pnl.get(dt, 0) + pnl
            pos["current_price"] = close

            pct_change = (close - entry_price) / entry_price if entry_price > 0 else 0
            stop_pct = getattr(risk, "stop_loss_pct", 0.0) or 0.0
            profit_pct = getattr(risk, "take_profit_pct", 0.0) or 0.0
            if pct_change <= -stop_pct or (profit_pct > 0 and pct_change >= profit_pct):
                to_close.append(sym)

        for sym in to_close:
            pos = positions[sym]
            df_sym = df_by_sym[sym]
            if not self._cn_trade_allowed(risk, sym, df_sym, dt, "SELL"):
                continue
            close = df_sym.loc[dt, "Close"]
            exec_price = self._slippage_price(close, "sell", costs.slippage_bps)
            exec_price * pos["shares"]
            trades.append({
                "date": dt,
                "symbol": sym,
                "action": "SELL",
                "price": exec_price,
                "shares": pos["shares"],
                "pnl": (exec_price - pos["entry_price"]) * pos["shares"],
            })
            del positions[sym]

    def _process_entries(self, dt: str, i: int, cal: list, positions: dict, df_by_sym: dict,
                         sig_map: dict, filt_map: dict, atr_map: dict, cash: float, max_pos: int,
                         risk: dict, sizing: dict, costs: dict, trades: list, daily_pnl: dict):
        if len(positions) >= max_pos:
            return
        candidates = []
        for sym in df_by_sym:
            if sym in positions:
                continue
            if sym not in sig_map or dt not in sig_map[sym].index:
                continue
            signal = sig_map[sym].loc[dt]
            if signal > 0 and filt_map.get(sym, {}).get(dt, True):
                candidates.append(sym)

        for sym in candidates[:max_pos - len(positions)]:
            df = df_by_sym[sym]
            if dt not in df.index:
                continue
            if not self._cn_trade_allowed(risk, sym, df, dt, "BUY"):
                continue
            close = df.loc[dt, "Close"]
            exec_price = self._slippage_price(close, "buy", costs.slippage_bps)
            shares = round_shares_for_market(cash / len(candidates), exec_price, "SH")
            if shares > 0:
                notional = exec_price * shares
                cost = self._buy_costs(notional, costs)
                if cash >= notional + cost:
                    cash -= notional + cost
                    positions[sym] = {
                        "entry_date": dt,
                        "entry_price": exec_price,
                        "shares": shares,
                        "current_price": close,
                    }
                    trades.append({
                        "date": dt,
                        "symbol": sym,
                        "action": "BUY",
                        "price": exec_price,
                        "shares": shares,
                        "pnl": 0,
                    })

    def _calc_pos_value(self, pos: dict, df: pd.DataFrame, dt: str) -> float:
        if dt not in df.index:
            return 0
        return df.loc[dt, "Close"] * pos["shares"]

    def _calc_shares(self, cash: float, price: float, sizing) -> int:
        weight = getattr(sizing, "default_weight", None) or getattr(sizing, "max_weight", 0.1)
        target_value = cash * weight
        shares = int(target_value / price) if price > 0 else 0
        return round_shares_for_market(shares, market="SH")

    def _should_stop_loss(self, dt: date, df: pd.DataFrame, i: int, atr: pd.Series, risk: dict) -> bool:
        if i < 1 or dt not in df.index:
            return False
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        pct_change = (curr["Close"] - prev["Close"]) / prev["Close"] if prev["Close"] > 0 else 0
        return pct_change <= -risk.stop_loss_pct

    def _should_take_profit(self, dt: date, df: pd.DataFrame, i: int, risk: dict) -> bool:
        if i < 1 or dt not in df.index:
            return False
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        pct_change = (curr["Close"] - prev["Close"]) / prev["Close"] if prev["Close"] > 0 else 0
        take_profit_pct = getattr(risk, "take_profit_pct", 0.0) or 0.0
        return take_profit_pct > 0 and pct_change >= take_profit_pct

    def _compute_metrics(self, equity_curve: list[dict], initial_capital: float, trades: list) -> dict:
        if not equity_curve:
            return {
                "final_value": initial_capital,
                "total_return": 0,
                "annual_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "stock_data": {},
                "equity_curve": [],
            }

        values = [float(e["value"]) for e in equity_curve]
        final_value = values[-1]
        total_return = (final_value - initial_capital) / initial_capital * 100 if initial_capital > 0 else 0
        max_dd = calculate_max_drawdown(values)
        sharpe = calculate_sharpe_ratio(values)
        total_days = max(1, len(equity_curve))
        annual_return = calculate_annual_return(initial_capital, final_value, float(total_days))

        return {
            "final_value": round(final_value, 2),
            "total_return": round(total_return, 2),
            "annual_return": round(annual_return, 2),
            "max_drawdown": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 4),
            "sharpe": round(sharpe, 4),
            "total_trades": len(trades),
            "equity_curve": equity_curve,
        }

    def _empty_result(self, capital: float) -> dict:
        return {
            "metrics": {
                "final_value": capital,
                "total_return": 0,
                "annual_return": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "stock_data": {},
                "equity_curve": [],
            },
            "trades": [],
            "stock_data": {},
            "equity_curve": [],
        }
