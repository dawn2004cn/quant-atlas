from __future__ import annotations
"""信号旗：全市场多策略买点扫描 + 股票池落盘。"""


import os
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from app.core.factory import StrategyFactory
from app.core.risk_controls import RiskControlParams, compute_liquidity_filters
from app.domain.enums import MarketCode
from app.domain.ports.stock_cache_port import StockCachePort
from app.domain.ports.signal_flag_pool_port import SignalFlagPoolRepository


_MAX_WORKERS = max(2, min(os.cpu_count() or 4, 8))


_LONG_CATS = frozenset({"趋势突破", "机构资金", "动量成长"})
_MID_CATS = frozenset({"震荡波段", "均值回归", "动量回调"})
_SHORT_CATS = frozenset({"恐慌抄底", "短线异动"})


def _horizon_bucket(category: str) -> str:
    c = (category or "").strip()
    if c in _LONG_CATS: return "long"
    if c in _SHORT_CATS: return "short"
    return "mid"


def _prepare_df(history: list[dict[str, Any]]) -> pd.DataFrame | None:
    if not history or len(history) < 30: return None
    df = pd.DataFrame(history)
    col_map = {c.lower(): c for c in df.columns}
    df.rename(columns={
        col_map.get("date", "date"): "Date",
        col_map.get("open", "open"): "Open",
        col_map.get("high", "high"): "High",
        col_map.get("low", "low"): "Low",
        col_map.get("close", "close"): "Close",
        col_map.get("volume", "volume"): "Volume",
    }, inplace=True)
    return df


def _last_signal(sig_df: pd.DataFrame) -> int:
    if "Signal" not in sig_df.columns or sig_df.empty: return 0
    try:
        v = int(sig_df["Signal"].iloc[-1])
        return v if v in (-1, 0, 1) else 0
    except (TypeError, ValueError):
        return 0


def _qlib_ma_cross_flags(df: pd.DataFrame) -> tuple[bool, bool]:
    close = pd.to_numeric(df["Close"], errors="coerce")
    if len(close) < 22 or close.isna().all(): return False, False
    ma5, ma20 = close.rolling(5).mean(), close.rolling(20).mean()
    if ma5.isna().iloc[-1] or ma20.isna().iloc[-1]: return False, False
    buy = bool(ma5.iloc[-1] > ma20.iloc[-1] and ma5.iloc[-2] <= ma20.iloc[-2])
    sell = bool(ma5.iloc[-1] < ma20.iloc[-1] and ma5.iloc[-2] >= ma20.iloc[-2])
    return buy, sell


def _safety_score(*, change_pct: float, pe: float, pb: float, buy_count: int, sell_count: int = 0) -> float:
    score = 52.0
    if change_pct > 0: score += 6
    if change_pct < -7: score -= 10
    if 0 < pe < 45: score += 8
    if pe > 90: score -= 12
    if 0 < pb < 6: score += 5
    if pb > 10: score -= 6
    score += min(buy_count, 5) * 2.0
    score += min(sell_count, 4) * 1.0
    return max(0.0, min(100.0, round(score, 1)))


def _strip_cn_code(raw: str) -> str:
    from app.domain.shared.symbol_normalizer import SymbolNormalizer

    return SymbolNormalizer.to_db_code(raw)


@dataclass
class SignalFlagScanSummary:
    pool_date: str
    scanned: int
    hits: int
    persisted: int
    message: str


def _scan_chunk_worker(
    strat_names: list[tuple[str, str]],
    chunk_data: list[tuple[str, dict, dict]],
    enable_qlib: bool,
    d0: str,
    start: str,
) -> list[tuple[str, dict]]:
    from app.core.factory import StrategyFactory
    risk = RiskControlParams()
    strategies = {sid: StrategyFactory.create_instance(sid) for sid, _ in strat_names if sid != "__QLIB__"}
    strategies = {sid: s for sid, s in strategies.items() if s is not None}
    results: dict[str, dict] = {}
    for code, meta, raw_df in chunk_data:
        df = _prepare_df_from_dict(raw_df)
        if df is None:
            continue
        code_hit: dict = {"buy": [], "sell": [],
            "hz": {"long": {"buy": [], "sell": []}, "mid": {"buy": [], "sell": []}, "short": {"buy": [], "sell": []}}}
        for sid, strat in strategies.items():
            try:
                sig_df = strat.generate_signals(df)
            except Exception:
                continue
            sig = _last_signal(sig_df)
            if sig == 0:
                continue
            bucket, label = _horizon_bucket(strat.category), f"{sid}:{strat.name}"
            if sig == 1:
                allowed = compute_liquidity_filters(df, p=risk)
                if len(allowed) and not bool(allowed.iloc[-1]):
                    continue
                code_hit["buy"].append({"id": sid, "name": strat.name})
                code_hit["hz"][bucket]["buy"].append(label)
            elif sig == -1:
                code_hit["sell"].append({"id": sid, "name": strat.name})
                code_hit["hz"][bucket]["sell"].append(label)
        if enable_qlib:
            qb, qs = _qlib_ma_cross_flags(df)
            if qb:
                code_hit["buy"].append({"id": "QLIB_MA5_20", "name": "Qlib · MA5 上穿 MA20"})
                code_hit["hz"]["long"]["buy"].append("QLIB_MA5_20:Qlib · MA5 上穿 MA20")
            if qs:
                code_hit["sell"].append({"id": "QLIB_MA5_20", "name": "Qlib · MA5 下穿 MA20"})
                code_hit["hz"]["long"]["sell"].append("QLIB_MA5_20:Qlib · MA5 下穿 MA20")
        if code_hit["buy"] or code_hit["sell"]:
            results[code] = code_hit
    return list(results.items())


def _prepare_df_from_dict(raw: dict) -> pd.DataFrame | None:
    df = pd.DataFrame(raw)
    needed = {"Date", "Open", "High", "Low", "Close", "Volume"}
    if needed.issubset(df.columns) and len(df) >= 30:
        return df
    return None


class SignalFlagScannerService:
    def __init__(self, *, stock_service: Any, stock_cache: StockCachePort, repository: SignalFlagPoolRepository, enable_qlib: bool = False) -> None:
        self._stock_service = stock_service
        self._stock_cache = stock_cache
        self._repo = repository
        self._enable_qlib = enable_qlib
        self._risk = RiskControlParams()

    def get_scan_universe(self, market: MarketCode, max_stocks: int = 800) -> list[dict[str, Any]]:
        rows = self._stock_cache.get_all_stocks(max_age_minutes=2880)
        ranked = []
        for r in rows:
            key = str(r.get("code", ""))
            code = _strip_cn_code(key)
            if not code or len(code) < 4: continue
            ranked.append({**r, "_scan_code": code})

        ranked.sort(key=lambda x: float(x.get("amount") or 0), reverse=True)
        hard_cap = max(800, min(int(os.getenv("SIGNAL_FLAG_UNIVERSE_HARD_CAP", "8000")), 20000))
        lim = min(len(ranked), hard_cap) if int(max_stocks or 0) <= 0 else max(50, min(int(max_stocks), hard_cap))
        return ranked[:lim]

    def _scan_single_stock_for_strategy(
        self, meta: dict, strat_id: str, strat: Any, *, df: pd.DataFrame, d0: str, start: str
    ) -> tuple | None:
        try:
            sig_df = strat.generate_signals(df)
        except Exception:
            return None
        sig = _last_signal(sig_df)
        if sig == 0:
            return None
        bucket, label = _horizon_bucket(strat.category), f"{strat_id}:{strat.name}"
        if sig == 1:
            allowed = compute_liquidity_filters(df, p=self._risk)
            if len(allowed) and not bool(allowed.iloc[-1]):
                return None
            return ("buy", bucket, label, strat_id, strat.name)
        elif sig == -1:
            return ("sell", bucket, label, strat_id, strat.name)
        return None

    def _strategy_scan(self, strat_id: str, strat: Any, stock_dfs: list, *, d0: str, start: str) -> dict:
        code_hits = {}
        for code_key, meta, df in stock_dfs:
            r = self._scan_single_stock_for_strategy(
                meta, strat_id, strat, df=df, d0=d0, start=start
            )
            if r is not None:
                code_hits[code_key] = r
        return {strat_id: code_hits}

    def _fetch_one_stock(
        self, meta: dict, *, start: str, d0: str, market: MarketCode, lookback_days: int
    ) -> tuple | None:
        code = meta.get("_scan_code") or _strip_cn_code(str(meta.get("code", "")))
        if not code:
            return None
        history = self._stock_service.get_bars_between(code, market, start, d0)
        if not history:
            history = self._stock_cache.get_stock_history_for_code(code, limit=lookback_days + 60)
        df = _prepare_df(history)
        if df is None or len(df) < 30:
            return None
        return (code, meta, df)

    def _prepare_stock_dfs(
        self, universe: list, *, start: str, d0: str, market: MarketCode, lookback_days: int
    ) -> list:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS * 2) as pool:
            futures = {
                pool.submit(self._fetch_one_stock, meta, start=start, d0=d0, market=market, lookback_days=lookback_days)
                for meta in universe
            }
            out = []
            for f in as_completed(futures):
                try:
                    r = f.result()
                    if r is not None:
                        out.append(r)
                except Exception:
                    continue
        return out

    def _qlib_strategy_scan(self, stock_dfs: list, *, d0: str, start: str) -> dict:
        code_hits = {}
        for code_key, meta, df in stock_dfs:
            qb, qs = _qlib_ma_cross_flags(df)
            if not qb and not qs:
                continue
            if code_key not in code_hits:
                hz = {"long": {"buy": [], "sell": []}, "mid": {"buy": [], "sell": []}, "short": {"buy": [], "sell": []}}
                if qb:
                    code_hits[code_key] = {
                        "buy": [{"id": "QLIB_MA5_20", "name": "Qlib · MA5 上穿 MA20"}],
                        "sell": [{"id": "QLIB_MA5_20", "name": "Qlib · MA5 下穿 MA20"}] if qs else [],
                        "hz": hz,
                    }
                    code_hits[code_key]["hz"]["long"]["buy"].append("QLIB_MA5_20:Qlib · MA5 上穿 MA20")
                if qs:
                    if code_key not in code_hits:
                        code_hits[code_key] = {"buy": [], "sell": [], "hz": hz}
                    code_hits[code_key]["sell"].append({"id": "QLIB_MA5_20", "name": "Qlib · MA5 下穿 MA20"})
                    code_hits[code_key]["hz"]["long"]["sell"].append("QLIB_MA5_20:Qlib · MA5 下穿 MA20")
        return code_hits

    def scan_batch(self, universe: list[dict[str, Any]], market: MarketCode, pool_date: str, lookback_days: int) -> list[dict[str, Any]]:
        d0 = pool_date[:10]
        start = (datetime.strptime(d0, "%Y-%m-%d") - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        strategies = list(StrategyFactory.iter_registered_instances())
        stock_dfs = self._prepare_stock_dfs(universe, start=start, d0=d0, market=market, lookback_days=lookback_days)

        chunk_size = max(50, len(stock_dfs) // (_MAX_WORKERS * 2))
        chunks = [stock_dfs[i:i + chunk_size] for i in range(0, len(stock_dfs), chunk_size)]

        strat_names = [(sid, strat.__class__.__name__) for sid, strat in strategies]

        with ProcessPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = []
            for chunk in chunks:
                chunk_data = [(code, meta, df.to_dict("list")) for code, meta, df in chunk]
                futures.append(pool.submit(
                    _scan_chunk_worker, strat_names, chunk_data,
                    self._enable_qlib, d0, start,
                ))
            raw_results = []
            for f in as_completed(futures):
                try:
                    raw_results.extend(f.result())
                except Exception:
                    continue

        hit_map: dict = {}
        for code_key, hm in raw_results:
            if code_key not in hit_map:
                hit_map[code_key] = {"buy": [], "sell": [],
                    "hz": {"long": {"buy": [], "sell": []}, "mid": {"buy": [], "sell": []}, "short": {"buy": [], "sell": []}}}
            hit_map[code_key]["buy"].extend(hm.get("buy", []))
            hit_map[code_key]["sell"].extend(hm.get("sell", []))
            for period, sides in hm.get("hz", {}).items():
                for side, labels in sides.items():
                    hit_map[code_key]["hz"][period][side].extend(labels)

        results = []
        code_to_meta = {code: meta for code, meta, _ in stock_dfs}
        code_to_df = {code: df for code, _meta, df in stock_dfs}
        for code_key, hm in hit_map.items():
            if not hm["buy"] and not hm["sell"]:
                continue
            meta = code_to_meta.get(code_key) or {}
            df = code_to_df.get(code_key)
            results.append({
                "code": code_key,
                "name": str(meta.get("name") or code_key),
                "price": float(meta.get("price") or (df["Close"].iloc[-1] if df is not None else 0) or 0),
                "change_pct": float(meta.get("change_pct") or 0),
                "volume": float(meta.get("volume") or 0), "amount": float(meta.get("amount") or 0),
                "turnover": float(meta.get("turnover") or 0), "source": str(meta.get("source") or "cache"),
                "industry": str(meta.get("industry") or ""), "pe": float(meta.get("pe") or 0), "pb": float(meta.get("pb") or 0),
                "signal_strategies": hm["buy"], "signal_strategies_sell": hm["sell"],
                "long_horizon": hm["hz"]["long"], "mid_horizon": hm["hz"]["mid"], "short_horizon": hm["hz"]["short"],
                "safety_score": _safety_score(
                    change_pct=float(meta.get("change_pct") or 0),
                    pe=float(meta.get("pe") or 0), pb=float(meta.get("pb") or 0),
                    buy_count=len(hm["buy"]), sell_count=len(hm["sell"]),
                ),
                "extra_snapshot": {
                    "amplitude": float(meta.get("amplitude") or 0),
                    "volume_ratio": float(meta.get("volume_ratio") or 0),
                    "prev_close": float(meta.get("prev_close") or 0),
                    "total_market_cap": float(meta.get("total_market_cap") or 0),
                    "history_bars": len(df) if df is not None else 0,
                    "scan_end": d0, "scan_start": start,
                },
            })

        return results

    def finalize_pool(self, pool_date: str, rows: list[dict[str, Any]]) -> int:
        return self._repo.replace_pool(pool_date[:10], rows)

    def run_scan(self, *, market: MarketCode = MarketCode.CN, pool_date: str | None = None, max_stocks: int = 800, lookback_days: int = 160) -> SignalFlagScanSummary:
        d0 = (pool_date or datetime.now().strftime("%Y-%m-%d"))[:10]
        if market != MarketCode.CN:
            return SignalFlagScanSummary(pool_date=d0, scanned=0, hits=0, persisted=0, message="仅支持 A 股。")

        universe = self.get_scan_universe(market, max_stocks)
        hits = self.scan_batch(universe, market, d0, lookback_days)
        n = self.finalize_pool(d0, hits)
        return SignalFlagScanSummary(pool_date=d0, scanned=len(universe), hits=len(hits), persisted=n, message=f"扫描 {len(universe)} 只，命中 {len(hits)} 条，已写入 {d0}。")

    def list_dates(self, *, limit: int = 120) -> list[str]: return self._repo.list_dates(limit=limit)
    def get_pool(self, pool_date: str) -> list[dict[str, Any]]: return self._repo.get_pool(pool_date)
