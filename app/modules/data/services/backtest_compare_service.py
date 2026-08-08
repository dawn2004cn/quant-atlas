from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""平台信号回测 vs Qlib TopkDropoutStrategy 官方回测对比。"""


from typing import Any

import pandas as pd

from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider
from app.models import ALL_STRATEGIES
from app.modules.data.services.qlib_service import QlibService
from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService


def _cn_symbol_to_qlib_instrument(symbol: str) -> str:
    s = symbol.strip().upper().replace(".SH", "").replace(".SZ", "")
    if s.startswith("SH") or s.startswith("SZ"):
        return s
    if len(s) == 6 and s.isdigit():
        if s.startswith(("5", "6", "9")):
            return "SH" + s
        return "SZ" + s
    return "SH" + s


def _resolve_strategy(strategy_id: str):
    sid = (strategy_id or "").strip().lower()
    for m in ALL_STRATEGIES:
        if sid in m.name.lower() or sid in m.__class__.__name__.lower():
            return m
    return ALL_STRATEGIES[0]


def _equity_curve_from_signals(df: pd.DataFrame, initial_capital: float) -> list[dict[str, Any]]:
    cash = float(initial_capital)
    position = 0
    curve: list[dict[str, Any]] = []
    for i in range(len(df)):
        row = df.iloc[i]
        signal = int(row.get("Signal", 0) or 0)
        price = float(row["Close"])
        if signal == 1 and position == 0:
            position = int(cash // price) if price > 0 else 0
            cash -= position * price
        elif signal == -1 and position > 0:
            cash += position * price
            position = 0
        equity = cash + position * price
        d = row["Date"]
        ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)[:10]
        curve.append({"date": ds, "equity": round(equity, 2)})
    return curve


class BacktestCompareService:
    def __init__(
        self,
        *,
        strategy_service: StrategyApplicationService,
        qlib_service: QlibService,
        market_provider: MarketDataProvider,
    ) -> None:
        self._strategy = strategy_service
        self._qlib = qlib_service
        self._market = market_provider

    def compare(
        self,
        *,
        strategy_id: str,
        symbol: str,
        start: str,
        end: str,
        initial_capital: float,
        enable_qlib: bool,
    ) -> GenericResponseDTO:
        sym = str(symbol).strip()
        legacy = self._strategy.backtest(
            symbol=sym,
            strategy_name=strategy_id,
            start=start,
            end=end,
            initial_capital=float(initial_capital),
        )
        metrics = legacy.get("metrics") or {}
        trades = legacy.get("trades") or []

        sig_df: pd.DataFrame | None = None
        try:
            history = self._market.get_stock_history(sym, MarketCode.CN, start, end)
            if history:
                df = pd.DataFrame(history)
                col_map = {c.lower(): c for c in df.columns}
                df.rename(
                    columns={
                        col_map.get("date", "date"): "Date",
                        col_map.get("open", "open"): "Open",
                        col_map.get("high", "high"): "High",
                        col_map.get("low", "low"): "Low",
                        col_map.get("close", "close"): "Close",
                        col_map.get("volume", "volume"): "Volume",
                    },
                    inplace=True,
                )
                strat = _resolve_strategy(strategy_id)
                sig_df = strat.generate_signals(df)
        except Exception:  # noqa: BLE001
            sig_df = None

        platform_equity: list[dict[str, Any]] = []
        if sig_df is not None and not sig_df.empty and "Close" in sig_df.columns:
            platform_equity = _equity_curve_from_signals(sig_df, float(initial_capital))

        platform_block: dict[str, Any] = {
            "ok": True,
            "strategy": legacy.get("strategy"),
            "metrics": {
                "final_value": metrics.get("final_value"),
                "total_return": metrics.get("total_return"),
                "annual_return": metrics.get("annual_return"),
                "max_drawdown": metrics.get("max_drawdown"),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
            },
            "equity_curve": platform_equity,
            "trades_count": len(trades),
            "stock_data": metrics.get("stock_data") or {},
        }

        inst = _cn_symbol_to_qlib_instrument(sym)
        qlib_block: dict[str, Any] = {
            "ok": False,
            "path": "disabled",
            "metrics": {},
            "equity_curve": [],
            "message": "",
        }

        if not enable_qlib:
            qlib_block["message"] = "ENABLE_QLIB 未开启"
            return {
                "symbol": sym,
                "qlib_instrument": inst,
                "strategy_id": strategy_id,
                "period": legacy.get("period") or {"start": start, "end": end},
                "platform": platform_block,
                "qlib": qlib_block,
            }

        if sig_df is None or sig_df.empty:
            qlib_block["path"] = "failed"
            qlib_block["message"] = "无法生成策略信号或行情为空"
            return {
                "symbol": sym,
                "qlib_instrument": inst,
                "strategy_id": strategy_id,
                "period": legacy.get("period") or {"start": start, "end": end},
                "platform": platform_block,
                "qlib": qlib_block,
            }

        try:
            records = QlibService.platform_signal_rows_from_dataframe(sig_df, instrument=inst)
        except Exception as exc:  # noqa: BLE001
            qlib_block["path"] = "failed"
            qlib_block["message"] = f"信号转换失败: {exc}"
            return {
                "symbol": sym,
                "qlib_instrument": inst,
                "strategy_id": strategy_id,
                "period": legacy.get("period") or {"start": start, "end": end},
                "platform": platform_block,
                "qlib": qlib_block,
            }

        if not records:
            qlib_block["path"] = "failed"
            qlib_block["message"] = "信号记录为空"
            return {
                "symbol": sym,
                "qlib_instrument": inst,
                "strategy_id": strategy_id,
                "period": legacy.get("period") or {"start": start, "end": end},
                "platform": platform_block,
                "qlib": qlib_block,
            }

        integrated = self._qlib.integrate_existing_strategy(
            {
                "records": records,
                "instrument": inst,
                "run_backtest": True,
                "start_time": start,
                "end_time": end,
                "account": float(initial_capital),
                "benchmark": "SH000300",
                "topk": 1,
                "n_drop": 0,
            }
        )
        qbt = integrated.get("qlib_backtest") or {}
        if isinstance(qbt, dict) and qbt.get("ok"):
            curve_raw = qbt.get("equity_curve") or []
            norm_curve = []
            for p in curve_raw:
                if isinstance(p, dict):
                    dt = p.get("date")
                    acct = p.get("account")
                    if acct is not None:
                        norm_curve.append({"date": dt, "equity": float(acct)})
            qlib_block = {
                "ok": True,
                "path": "official",
                "metrics": qbt.get("metrics") or {},
                "equity_curve": norm_curve,
                "message": "",
            }
        else:
            err = ""
            if isinstance(qbt, dict):
                err = str(qbt.get("message") or qbt.get("error") or "")
            if not err:
                err = str(integrated.get("backtest_error") or integrated.get("message") or "qlib 回测失败")
            qlib_block = {
                "ok": False,
                "path": "failed",
                "metrics": {},
                "equity_curve": [],
                "message": err,
            }

        return {
            "symbol": sym,
            "qlib_instrument": inst,
            "strategy_id": strategy_id,
            "period": legacy.get("period") or {"start": start, "end": end},
            "platform": platform_block,
            "qlib": qlib_block,
        }
