from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Qlib 路线图阶段 1：导出数据、状态、示例因子、简易回测（无需安装 pyqlib 即可联调）。"""


import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.ports import QlibDataProviderPort
from app.domain.shared.qlib_symbol_map import qlib_instrument_to_symbol, to_qlib_instrument
from app.modules.system.services.helpers.qlib_access import create_qlib_data_adapter
from .qlib_sync_helpers import QlibIngestMeta, _safe_history_table_sql, _list_all_stock_codes_from_mysql, _timescale_bars_to_history_rows
from .qlib_bin_exporter import QlibBinExporter

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class QlibPipelineService:
    """写入 ``instance/qlib_export`` CSV；元数据 ``config/qlib_pipeline_meta.json``。"""

    def __init__(
        self,
        data_access: MarketDataAccess | QlibDataProviderPort,
        *,
        base_dir: Path,
        tdx_root_path: str | None = None,
        stock_cache: Any | None = None,
    ) -> None:
        if hasattr(data_access, "fetch_daily_bars"):
            self._adapter = data_access
        else:
            self._adapter = create_qlib_data_adapter(
                data_access,
                tdx_root_path=tdx_root_path,
                stock_cache=stock_cache,
            )
        self._base = Path(base_dir)
        self.export_dir = self._base / "instance" / "qlib_export"
        self.qlib_bin_dir = self._base / "instance" / "qlib_bin"
        self.meta_path = self._base / "config" / "qlib_pipeline_meta.json"
        legacy_meta = self._base / "instance" / "qlib_pipeline_meta.json"
        if not self.meta_path.is_file() and legacy_meta.is_file():
            self.meta_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(legacy_meta, self.meta_path)
            logger.info("qlib: migrated pipeline meta %s -> %s", legacy_meta, self.meta_path)
        self._bin_exporter = QlibBinExporter(self._adapter, base_dir=self._base, tdx_root_path=tdx_root_path, stock_cache=stock_cache)

    @staticmethod
    def pyqlib_importable() -> bool:
        try:
            import qlib  # noqa: F401, PLC0415
        except ImportError:
            return False
        return True

    def _load_meta(self) -> GenericResponseDTO:
        if not self.meta_path.exists():
            return {}
        try:
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _save_meta(self, meta: QlibIngestMeta) -> None:
        self.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(meta.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def status(self) -> GenericResponseDTO:
        self.export_dir.mkdir(parents=True, exist_ok=True)
        csv_files = sorted(self.export_dir.glob("*.csv"))
        raw = self._load_meta()
        cal = self.qlib_bin_dir / "calendars" / "day.txt"
        return {
            "export_dir": str(self.export_dir.resolve()),
            "qlib_bin_dir": str(self.qlib_bin_dir.resolve()),
            "qlib_bin_ready": cal.is_file() and cal.stat().st_size > 0,
            "csv_count": len(csv_files),
            "instruments_on_disk": [p.stem for p in csv_files],
            "pyqlib_installed": self.pyqlib_importable(),
            "last_meta": raw,
        }

    def ingest_symbols(
        self,
        symbols: list[str],
        market: MarketCode,
        *,
        period: str = "2y",
        merge_existing: bool = False,
    ) -> QlibIngestMeta:
        """每个标的写一个 ``{SH600519}.csv``，列: date,open,high,low,close,volume。

        ``merge_existing=True`` 时与已有 CSV 按 ``date`` 合并，同日期保留本次拉取（便于增量跑任务）。
        """
        self.export_dir.mkdir(parents=True, exist_ok=True)
        instruments: list[str] = []
        row_counts: dict[str, int] = {}
        notes: list[str] = []
        gmin: str | None = None
        gmax: str | None = None
        for sym in symbols:
            sym = (sym or "").strip()
            if not sym:
                continue
            inst = to_qlib_instrument(sym, market)
            path = self.export_dir / f"{inst}.csv"
            bars, ev = self._adapter.fetch_daily_bars(sym, market, period=period)
            notes.append(f"{inst}: {ev[:200]}")
            if not bars:
                row_counts[inst] = 0
                if merge_existing and path.exists():
                    logger.info("ingest %s: 本次无 K 线，保留磁盘 CSV", inst)
                continue
            df = pd.DataFrame(bars)
            if merge_existing and path.exists():
                try:
                    df_old = pd.read_csv(path, parse_dates=["date"])
                    n_old = len(df_old)
                    df = (
                        pd.concat([df_old, df], ignore_index=True)
                        .assign(date=lambda x: pd.to_datetime(x["date"]))
                        .drop_duplicates(subset=["date"], keep="last")
                        .sort_values("date")
                        .reset_index(drop=True)
                    )
                    logger.info(
                        "ingest %s: merge_existing 合并 CSV，旧 %d 行 → 合并后 %d 行",
                        inst,
                        n_old,
                        len(df),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning("ingest %s: 合并旧 CSV 失败，仅写入本次拉取: %s", inst, exc)
            df.to_csv(path, index=False)
            instruments.append(inst)
            row_counts[inst] = len(df)
            d0 = str(df.iloc[0]["date"])[:10]
            d1 = str(df.iloc[-1]["date"])[:10]
            gmin = d0 if gmin is None or d0 < gmin else gmin
            gmax = d1 if gmax is None or d1 > gmax else gmax

        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        meta = QlibIngestMeta(
            last_ingest_at=now,
            market=market.value,
            instruments=instruments,
            date_min=gmin or "",
            date_max=gmax or "",
            row_counts=row_counts,
            evidence_notes=notes[:50],
        )
        self._save_meta(meta)
        return meta

    def write_meta_only(
        self,
        *,
        market: MarketCode,
        instruments: list[str],
        date_min: str,
        date_max: str,
        row_counts: dict[str, int] | None = None,
        evidence_notes: list[str] | None = None,
    ) -> None:
        """仅写入 meta（不拉行情、不写 CSV），用于“外部管线已生成 CSV”场景。"""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        meta = QlibIngestMeta(
            last_ingest_at=now,
            market=market.value,
            instruments=list(instruments or []),
            date_min=str(date_min or ""),
            date_max=str(date_max or ""),
            row_counts=dict(row_counts or {}),
            evidence_notes=list(evidence_notes or [])[:50],
        )
        self._save_meta(meta)

    def write_meta_touch(self, *, evidence_notes: list[str] | None = None) -> None:
        """增量运行时，保留 instruments 等，仅刷新 last_ingest_at 与证据说明。"""
        st = self.status()
        raw = st.get("last_meta") or {}
        market = str(raw.get("market") or MarketCode.CN.value)
        instruments = [str(x).strip() for x in (raw.get("instruments") or []) if str(x).strip()]
        date_min = str(raw.get("date_min") or "")
        date_max = str(raw.get("date_max") or "")
        row_counts = raw.get("row_counts") if isinstance(raw.get("row_counts"), dict) else {}
        self.write_meta_only(
            market=MarketCode(market) if market in (m.value for m in MarketCode) else MarketCode.CN,
            instruments=instruments,
            date_min=date_min,
            date_max=date_max,
            row_counts={str(k): int(v) for k, v in (row_counts or {}).items() if str(k).strip()},
            evidence_notes=list(evidence_notes or []),
        )

    def factors(
        self,
        symbol: str,
        market: MarketCode,
        *,
        start: str | None = None,
        end: str | None = None,
        period: str = "2y",
    ) -> GenericResponseDTO:
        """示例因子：``MA5``、``RET1``（日收益），基于内存拉取或磁盘 CSV。"""
        inst = to_qlib_instrument(symbol, market)
        csv_path = self.export_dir / f"{inst}.csv"
        src_ev = ""
        if csv_path.exists():
            df = pd.read_csv(csv_path, parse_dates=["date"])
        else:
            bars, ev = self._adapter.fetch_daily_bars(symbol, market, period=period)
            df = self._adapter.bars_to_dataframe(bars)
            src_ev = ev
        if df.empty:
            return {"instrument": inst, "factors": [], "error": "no_bars", "evidence": src_ev}

        df = df.sort_values("date").reset_index(drop=True)
        if start:
            df = df[df["date"] >= pd.Timestamp(start)]
        if end:
            df = df[df["date"] <= pd.Timestamp(end)]
        df = df.reset_index(drop=True)
        df["MA5"] = df["close"].rolling(5, min_periods=1).mean()
        df["RET1"] = df["close"].pct_change()
        records: list[dict[str, Any]] = []
        for _, row in df.tail(120).iterrows():
            records.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "",
                    "close": float(row["close"]) if pd.notna(row["close"]) else None,
                    "MA5": float(row["MA5"]) if pd.notna(row["MA5"]) else None,
                    "RET1": float(row["RET1"]) if pd.notna(row["RET1"]) else None,
                }
            )
        out: dict[str, Any] = {
            "instrument": inst,
            "factors": ["MA5", "RET1"],
            "series": records,
            "source": "csv_disk" if csv_path.exists() else "live_fetch",
        }
        if not csv_path.exists():
            out["evidence"] = src_ev  # type: ignore[name-defined]
        return out

    def cross_section_factor_rank(
        self,
        market: MarketCode,
        *,
        top_n: int = 20,
        max_universe: int = 80,
        period: str = "2y",
    ) -> GenericResponseDTO:
        """基于 ``MA5`` / ``RET1`` / 收盘价的截面组合得分排序（``qlib_factors`` 数据源）。"""
        if market != MarketCode.CN:
            return {
                "candidates": [],
                "evidence": "cross_section_factor_rank 当前仅支持 CN。",
                "error": "market_not_cn",
            }

        meta = self._load_meta()
        raw_list: list[str] = list(meta.get("instruments") or [])
        if not raw_list:
            self.export_dir.mkdir(parents=True, exist_ok=True)
            raw_list = sorted({p.stem for p in self.export_dir.glob("*.csv") if p.stem})
        instruments = [str(x).strip() for x in raw_list if str(x).strip()][: max(max_universe, top_n)]

        if not instruments:
            return {
                "candidates": [],
                "evidence": "无标的：请先执行 qlib ingest 写入 instance/qlib_export。",
                "error": "no_instruments",
            }

        scored: list[tuple[str, str, float, str]] = []
        for inst in instruments:
            sym = qlib_instrument_to_symbol(inst, market)
            fac = self.factors(sym, market, period=period)
            if fac.get("error") == "no_bars":
                continue
            series = fac.get("series") or []
            if not series:
                continue
            last = series[-1]
            ma5 = last.get("MA5")
            cls = last.get("close")
            ret1 = last.get("RET1")
            if ma5 is None or cls is None or float(ma5) <= 0:
                continue
            bias = (float(cls) / float(ma5) - 1.0) * 100.0
            mom = (float(ret1) * 100.0) if isinstance(ret1, (int, float)) and ret1 == ret1 else 0.0
            score = bias * 0.6 + mom * 0.4
            reason = f"QLib MA5偏离{bias:.2f}% + RET1{mom:.2f}% ({fac.get('source')})"
            scored.append((sym, inst, score, reason))

        scored.sort(key=lambda x: x[2], reverse=True)
        top = scored[:top_n]
        candidates: list[dict[str, Any]] = []
        for sym, _inst, score, reason in top:
            candidates.append(
                {
                    "code": sym,
                    "name": sym,
                    "price": 0.0,
                    "score": round(score, 4),
                    "reason": reason,
                    "rating": "A" if score >= 2.0 else "B",
                    "buy_signals": ["MA5/RET1截面"],
                }
            )

        return {
            "candidates": candidates,
            "evidence": f"universe={len(instruments)} 有效={len(scored)} 因子=MA5,RET1,close",
            "source": "qlib_factors",
        }

    def simple_backtest(
        self,
        symbol: str,
        market: MarketCode,
        *,
        start: str,
        end: str,
        initial_capital: float = 100_000.0,
        period: str = "5y",
    ) -> GenericResponseDTO:
        """买入持有（首日收盘价建仓），与平台 backtest 关键 metrics 字段对齐。"""
        bars, ev = self._adapter.fetch_daily_bars(symbol, market, period=period)
        df = self._adapter.bars_to_dataframe(bars)
        if df.empty:
            return {
                "source": "qlib_pipeline_stub",
                "backtest_engine": "pandas_adapter_buy_hold",
                "strategy": "buy_hold",
                "symbol": symbol,
                "market": market.value,
                "period": {"start": start, "end": end},
                "metrics": {
                    "final_value": initial_capital,
                    "total_return": 0.0,
                    "annual_return": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "stock_data": {},
                },
                "trades": [],
                "error": "no_bars",
                "evidence": ev,
            }
        df = df[(df["date"] >= pd.Timestamp(start)) & (df["date"] <= pd.Timestamp(end))]
        df = df.reset_index(drop=True)
        if len(df) < 2:
            return {
                "source": "qlib_pipeline_stub",
                "backtest_engine": "pandas_adapter_buy_hold",
                "strategy": "buy_hold",
                "symbol": symbol,
                "market": market.value,
                "period": {"start": start, "end": end},
                "metrics": {
                    "final_value": initial_capital,
                    "total_return": 0.0,
                    "annual_return": 0.0,
                    "max_drawdown": 0.0,
                    "sharpe_ratio": 0.0,
                    "stock_data": {},
                },
                "trades": [],
                "error": "insufficient_bars",
                "evidence": ev,
            }
        p0 = float(df.iloc[0]["close"])
        p1 = float(df.iloc[-1]["close"])
        shares = initial_capital / p0 if p0 > 0 else 0.0
        final = shares * p1
        total_ret = (final / initial_capital - 1.0) if initial_capital > 0 else 0.0
        days = max(1, (df.iloc[-1]["date"] - df.iloc[0]["date"]).days)
        years = days / 365.25
        ann = ((final / initial_capital) ** (1 / years) - 1.0) if years > 0 and initial_capital > 0 else 0.0
        cummax = df["close"].cummax()
        dd = ((df["close"] / cummax) - 1.0).min() if len(df) else 0.0
        rets = df["close"].pct_change().dropna()
        sharpe = 0.0
        if len(rets) > 2 and rets.std() > 1e-12:
            sharpe = float((rets.mean() / rets.std()) * (252**0.5))
        return {
            "source": "qlib_pipeline_stub",
            "backtest_engine": "pandas_adapter_buy_hold",
            "strategy": "buy_hold",
            "symbol": symbol,
            "market": market.value,
            "period": {"start": start, "end": end},
            "metrics": {
                "final_value": round(final, 2),
                "total_return": round(total_ret * 100.0, 4),
                "annual_return": round(ann * 100.0, 4),
                "max_drawdown": round(float(dd) * 100.0, 4),
                "sharpe_ratio": round(sharpe, 6),
                "stock_data": {"bars_used": len(df), "entry_price": p0, "exit_price": p1},
            },
            "trades": [],
            "evidence": f"{ev} 简易买入持有（pandas 适配器，与平台 metrics 对齐）。",
        }

    def run_backtest(
        self,
        symbol: str,
        market: MarketCode,
        *,
        start: str,
        end: str,
        initial_capital: float = 100_000.0,
        period: str = "5y",
    ) -> GenericResponseDTO:
        """优先 pyqlib + ``qlib_bin`` 读 ``$close`` 做买入持有；失败则回退 ``simple_backtest``。

        返回始终含 ``backtest_engine`` 字段，便于 API/Agent 与 RD 门禁对齐。
        """
        st = self.status()
        if market == MarketCode.CN and self.pyqlib_importable() and st.get("qlib_bin_ready"):
            try:
                import qlib  # noqa: PLC0415
                from qlib.constant import REG_CN  # noqa: PLC0415
                from qlib.data import D  # noqa: PLC0415

                uri = str(self.qlib_bin_dir.resolve())
                qlib.init(provider_uri=uri, region=REG_CN)
                inst = to_qlib_instrument(symbol, market)
                df = D.features([inst], ["$close"], start_time=start, end_time=end, freq="day")
                if df is None or len(df) == 0:
                    raise ValueError("pyqlib features empty")
                if inst not in df.index.get_level_values(0):
                    raise ValueError(f"instrument {inst} missing in pyqlib frame")
                sub = df.loc[inst]
                closes = sub["$close"].dropna().astype(float)
                if len(closes) < 2:
                    raise ValueError("insufficient pyqlib closes")
                p0 = float(closes.iloc[0])
                p1 = float(closes.iloc[-1])
                shares = initial_capital / p0 if p0 > 0 else 0.0
                final = shares * p1
                total_ret = (final / initial_capital - 1.0) if initial_capital > 0 else 0.0
                idx = closes.index
                t0 = pd.Timestamp(idx[0])
                t1 = pd.Timestamp(idx[-1])
                days = max(1, int((t1 - t0).days))
                years = days / 365.25
                ann = ((final / initial_capital) ** (1 / years) - 1.0) if years > 0 and initial_capital > 0 else 0.0
                cummax = closes.cummax()
                dd = ((closes / cummax) - 1.0).min() if len(closes) else 0.0
                rets = closes.pct_change().dropna()
                sharpe = 0.0
                if len(rets) > 2 and float(rets.std()) > 1e-12:
                    sharpe = float((rets.mean() / rets.std()) * (252**0.5))
                return {
                    "source": "qlib_bin_pyqlib",
                    "backtest_engine": "pyqlib_bin_buy_hold",
                    "strategy": "buy_hold",
                    "symbol": symbol,
                    "market": market.value,
                    "period": {"start": start, "end": end},
                    "metrics": {
                        "final_value": round(final, 2),
                        "total_return": round(total_ret * 100.0, 4),
                        "annual_return": round(ann * 100.0, 4),
                        "max_drawdown": round(float(dd) * 100.0, 4),
                        "sharpe_ratio": round(sharpe, 6),
                        "stock_data": {"bars_used": len(closes), "entry_price": p0, "exit_price": p1},
                    },
                    "trades": [],
                    "evidence": f"pyqlib D.features 读取 qlib_bin URI={uri} instrument={inst} bars={len(closes)}。",
                }
            except Exception as exc:  # noqa: BLE001
                logger.warning("unified_buy_hold pyqlib path failed: %s", exc)

        res = self.simple_backtest(symbol, market, start=start, end=end, initial_capital=initial_capital, period=period)
        if isinstance(res, dict):
            res.setdefault("backtest_engine", "pandas_adapter_buy_hold")
        return res

    def dump_to_qlib_bin(
        self,
        *,
        max_workers: int = 8,
        overwrite: bool = False,
        include_fields: str = "open,high,low,close,volume,amount",
        incremental: bool | None = None,
    ) -> GenericResponseDTO:
        """委托 ``QlibBinExporter``：``qlib_export`` CSV → ``qlib_bin``。"""
        return self._bin_exporter.dump_to_qlib_bin(
            max_workers=max_workers,
            overwrite=overwrite,
            include_fields=include_fields,
            incremental=incremental,
        )

    def mysql_to_bin_sync(
        self,
        days_lookback: int = 5,
        limit_stocks: int | None = None,
        export_csv: bool = True,
    ) -> GenericResponseDTO:
        """Deprecated：历史入库已切 CSV→bin；保留委托以免旧调用方 AttributeError。"""
        logger.warning("mysql_to_bin_sync deprecated; use dump_to_qlib_bin (CSV→bin)")
        return self.dump_to_qlib_bin(incremental=days_lookback > 0)

    def unified_buy_hold_backtest(
        self,
        symbol: str,
        market: MarketCode,
        *,
        start: str,
        end: str,
        initial_capital: float = 100_000.0,
    ) -> GenericResponseDTO:
        return self.run_backtest(symbol, market, start=start, end=end, initial_capital=initial_capital)


__all__ = ["QlibPipelineService"]
