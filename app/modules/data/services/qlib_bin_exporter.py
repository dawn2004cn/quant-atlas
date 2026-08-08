from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool
from app.domain.dto.service_result import GenericResponseDTO
from app.domain.ports import QlibDataProviderPort
from app.modules.system.services.helpers.qlib_access import get_qlib_bin_dumper
from app.modules.data.services.qlib_sync_helpers import (
    _list_all_stock_codes_from_mysql,
    _safe_history_table_sql,
    _timescale_bars_to_history_rows,
)

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)


class QlibBinExporter:
    """将 CSV/MySQL 数据导出为 Qlib 二进制格式（``instance/qlib_bin``）。"""

    def __init__(
        self,
        data_access: MarketDataAccess | QlibDataProviderPort,
        *,
        base_dir: Path,
        tdx_root_path: str | None = None,
        stock_cache: Any | None = None,
    ) -> None:
        # 这些字段仅在 dump_to_qlib_bin / csv_to_bin_sync / mysql_to_bin_sync 中用到
        self._adapter = data_access
        self._base = Path(base_dir)
        self.export_dir = self._base / "instance" / "qlib_export"
        self.qlib_bin_dir = self._base / "instance" / "qlib_bin"
        self._tdx_root_path = tdx_root_path
        self._stock_cache = stock_cache

    @staticmethod
    def pyqlib_importable() -> bool:
        try:
            import qlib  # noqa: F401, PLC0415
        except ImportError:
            return False
        return True

    def dump_to_qlib_bin(
        self,
        *,
        max_workers: int = 8,
        overwrite: bool = False,
        include_fields: str = "open,high,low,close,volume,amount",
        incremental: bool | None = None,
    ) -> GenericResponseDTO:
        """将 ``instance/qlib_export/*.csv`` 转为 Qlib 二进制目录（``instance/qlib_bin``）。

        CSV 通常由 ``ingest_symbols`` 经 ``MarketDataAccess`` 拉取（含通达信链路）写入。
        依赖已安装 ``pyqlib``（``qlib.utils.fname_to_code`` 等）。

        ``incremental``：``None`` 时若已有 ``qlib_bin`` 日历与标的表则走增量（``DumpDataUpdate``，只追加新日期）；
        ``True`` 强制增量（不满足前提时回退全量并打日志）；``False`` 始终全量（``DumpDataAll``）。
        """
        if not self.pyqlib_importable():
            logger.error("dump_to_qlib_bin: pyqlib 未安装")
            return {
                "ok": False,
                "error": "pyqlib_not_installed",
                "message": "请安装 pyqlib（见 requirements-qlib.txt）后再执行 CSV→bin。",
                "qlib_bin_dir": str(self.qlib_bin_dir.resolve()),
                "mode": "none",
            }
        self.export_dir.mkdir(parents=True, exist_ok=True)
        csv_files = sorted(self.export_dir.glob("*.csv"))
        if not csv_files:
            logger.warning("dump_to_qlib_bin: qlib_export 下无 CSV")
            return {
                "ok": False,
                "error": "no_csv",
                "message": "qlib_export 下无 CSV，请先调用 /qlib/ingest。",
                "qlib_bin_dir": str(self.qlib_bin_dir.resolve()),
                "mode": "none",
            }

        cal = self.qlib_bin_dir / "calendars" / "day.txt"
        inst = self.qlib_bin_dir / "instruments" / "all.txt"
        bin_ready = (
            cal.is_file()
            and cal.stat().st_size > 0
            and inst.is_file()
            and inst.stat().st_size > 0
        )

        if overwrite:
            use_incremental = False
            mode = "full"
            logger.info("dump_to_qlib_bin: overwrite=True，全量重建 qlib_bin")
        elif incremental is False:
            use_incremental = False
            mode = "full"
            logger.info("dump_to_qlib_bin: incremental=False，全量 DumpDataAll")
        elif incremental is True:
            use_incremental = bin_ready
            mode = "incremental" if bin_ready else "full"
            if not bin_ready:
                logger.warning(
                    "dump_to_qlib_bin: 请求增量但 qlib_bin 不完整（缺 calendars/day 或 instruments/all），改为全量",
                )
            else:
                logger.info("dump_to_qlib_bin: 强制增量 DumpDataUpdate（仅处理 CSV 中晚于 bin 的日期）")
        else:
            use_incremental = bin_ready
            mode = "incremental" if bin_ready else "full"
            if bin_ready:
                logger.info("dump_to_qlib_bin: 自动选择增量 DumpDataUpdate")
            else:
                logger.info("dump_to_qlib_bin: 无已有 qlib_bin，全量 DumpDataAll")

        if overwrite and self.qlib_bin_dir.exists():
            shutil.rmtree(self.qlib_bin_dir, ignore_errors=False)
        self.qlib_bin_dir.mkdir(parents=True, exist_ok=True)

        kw = dict(
            data_path=str(self.export_dir.resolve()),
            qlib_dir=str(self.qlib_bin_dir.resolve()),
            freq="day",
            max_workers=max(1, int(max_workers)),
            include_fields=include_fields,
        )
        try:
            get_qlib_bin_dumper().dump(incremental=use_incremental, **kw)
        except Exception as exc:  # noqa: BLE001
            logger.exception("dump_to_qlib_bin: DumpData 执行失败 mode=%s", mode)
            return {
                "ok": False,
                "error": "dump_failed",
                "message": str(exc),
                "qlib_bin_dir": str(self.qlib_bin_dir.resolve()),
                "mode": mode,
            }

        cal = self.qlib_bin_dir / "calendars" / "day.txt"
        inst = self.qlib_bin_dir / "instruments" / "all.txt"
        logger.info(
            "dump_to_qlib_bin: 完成 mode=%s csv=%d calendar=%s",
            mode,
            len(csv_files),
            "ok" if cal.is_file() else "missing",
        )
        return {
            "ok": True,
            "mode": mode,
            "qlib_bin_dir": str(self.qlib_bin_dir.resolve()),
            "csv_used": len(csv_files),
            "calendar_file": str(cal) if cal.is_file() else "",
            "instruments_file": str(inst) if inst.is_file() else "",
        }

    def csv_to_bin_sync(self, limit_stocks: int | None = None) -> GenericResponseDTO:
        """从 CSV 文件同步数据到 Qlib 二进制目录。

        当 MySQL 数据不完整但 CSV 文件完整时使用此方法。
        """
        import pandas as pd

        bin_dir = self.qlib_bin_dir
        export_dir = self.export_dir
        features = ["open", "high", "low", "close", "volume", "amount"]

        # 获取所有 CSV 文件
        csv_files = list(export_dir.glob("*.csv"))
        stock_codes = [f.stem for f in csv_files]

        if limit_stocks:
            stock_codes = stock_codes[:limit_stocks]

        if not stock_codes:
            return {"ok": False, "error": "no_csv_files"}

        # 获取日期列表（从第一个 CSV 文件提取）
        sample_df = pd.read_csv(csv_files[0])
        dates = sorted(sample_df["date"].unique().tolist())

        # 写入日历
        cal_dir = bin_dir / "calendars"
        cal_dir.mkdir(parents=True, exist_ok=True)
        (cal_dir / "day.txt").write_text("\n".join(dates), encoding="utf-8")

        date_to_idx = {d: i for i, d in enumerate(dates)}
        total_days = len(dates)

        synced = 0

        for stock_code in stock_codes:
            csv_path = export_dir / f"{stock_code}.csv"
            if not csv_path.exists():
                continue

            try:
                df = pd.read_csv(csv_path)
                rows = df.to_dict("records")

                # 转换数据
                adjusted = []
                for row in rows:
                    r = {
                        "date": str(row["date"]),
                        "open": row.get("open", 0),
                        "high": row.get("high", 0),
                        "low": row.get("low", 0),
                        "close": row.get("close", 0),
                        "volume": row.get("volume", 0),
                        "amount": row.get("amount", 0),
                    }
                    adjusted.append(r)

                self._write_stock_to_bin(
                    stock_code, adjusted, bin_dir, export_dir,
                    features, date_to_idx, total_days, export_csv=False,
                )
                synced += 1
            except Exception as e:
                logger.warning("Failed to process %s: %s", stock_code, e, exc_info=True)

        return {
            "ok": True,
            "synced_stocks": synced,
            "total_days": total_days,
            "stocks_selected": len(stock_codes),
        }

    def mysql_to_bin_sync(self, days_lookback: int = 5, limit_stocks: int | None = None, export_csv: bool = True) -> GenericResponseDTO:
        """从 MySQL 数据库同步数据到 Qlib 二进制目录（可选导出 CSV 备份）。

        ``days_lookback`` > 0 时仅重导该窗口内有行情更新的标的（日历仍用全量交易日对齐 bin 下标）。

        优先查询 ``*_new`` 表（全量同步数据），回退到主表。
        """
        from datetime import date, timedelta

        from app.modules.system.services.helpers.tdx_data_repository_access import require_tdx_dayk_write_port
        from app.config import get_settings

        settings = get_settings()
        if not settings.use_mysql:
            return {"ok": False, "error": "mysql_not_enabled"}

        repo = require_tdx_dayk_write_port()
        bin_dir = self.qlib_bin_dir
        export_dir = self.export_dir
        features = ["open", "high", "low", "close", "volume", "amount"]

        dates = repo.list_history_calendar_dates()
        lookback = max(0, int(days_lookback or 0))

        # 直接从 *_new 表获取股票代码（全量同步数据更完整）
        stock_codes = _list_all_stock_codes_from_mysql(repo, limit_stocks)

        if not dates:
            return {"ok": False, "error": "no_data_in_mysql"}

        cal_dir = bin_dir / "calendars"
        cal_dir.mkdir(parents=True, exist_ok=True)
        (cal_dir / "day.txt").write_text("\n".join(dates), encoding="utf-8")

        date_to_idx = {d: i for i, d in enumerate(dates)}
        total_days = len(dates)

        # 优先查询 *_new 表，回退到主表
        table_map = {
            "stock_history_sh_new": [c for c in stock_codes if c.lower().startswith("sh")],
            "stock_history_sz_new": [c for c in stock_codes if c.lower().startswith("sz")],
            "stock_history_bj_new": [c for c in stock_codes if c.lower().startswith("bj")],
        }
        # 回退表
        fallback_map = {
            "stock_history_sh": [c for c in stock_codes if c.lower().startswith("sh")],
            "stock_history_sz": [c for c in stock_codes if c.lower().startswith("sz")],
            "stock_history_bj": [c for c in stock_codes if c.lower().startswith("bj")],
        }

        import threading as _thr

        synced = 0
        sync_lock = _thr.Lock()
        synced_codes: set[str] = set()

        def _process_table(table: str, codes: list[str]) -> int:
            if not codes:
                return 0
            rows = repo.fetch_history_rows(table, codes)
            n = 0
            current_code = None
            current_rows: list[dict[str, Any]] = []
            for row in rows:
                code = row["stock_code"]
                if code != current_code:
                    if current_code and current_rows:
                        adjusted = self._bin_adjusted_rows(current_rows, repo, current_code)
                        self._write_stock_to_bin(
                            current_code, adjusted, bin_dir, export_dir,
                            features, date_to_idx, total_days, export_csv,
                        )
                        with sync_lock:
                            synced_codes.add(current_code)
                        n += 1
                    current_code = code
                    current_rows = []
                current_rows.append(row)
            if current_code and current_rows:
                adjusted = self._bin_adjusted_rows(current_rows, repo, current_code)
                self._write_stock_to_bin(
                    current_code, adjusted, bin_dir, export_dir,
                    features, date_to_idx, total_days, export_csv,
                )
                with sync_lock:
                    synced_codes.add(current_code)
                n += 1
            return n

        with ThreadPoolExecutor(max_workers=3) as pool:
            results = pool.map(lambda tb_codes: _process_table(*tb_codes), table_map.items())
            for n in results:
                with sync_lock:
                    synced += n

        # 处理回退表（仅处理未同步的股票）
        remaining_map = {
            k: [c for c in v if c not in synced_codes]
            for k, v in fallback_map.items()
        }
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = pool.map(lambda tb_codes: _process_table(*tb_codes), remaining_map.items())
            for n in results:
                with sync_lock:
                    synced += n

        return {
            "ok": True,
            "synced_stocks": synced,
            "total_days": total_days,
            "csv_exported": export_csv,
            "days_lookback": lookback,
            "stocks_selected": len(stock_codes),
        }

    def _bin_adjusted_rows(
        self,
        rows: list[dict[str, Any]],
        repo: Any,
        stock_code: str,
    ) -> list[dict[str, Any]]:
        """qlib_bin 使用前复权：优先 Timescale ``market_bars_qfq`` 物化视图，否则 MySQL 因子计算。"""
        from app.config import get_settings

        settings = get_settings()
        use_ts_qfq = get_runtime_bool("QLIB_BIN_USE_TIMESCALE_QFQ", True)
        if not use_ts_qfq or not settings.use_timescaledb:
            return self._apply_qfq_adjustment(rows, repo, stock_code)
        try:
            from app.modules.system.services.helpers.timescale_bar_access import get_timescale_bar_port
            from app.infrastructure.repositories.postgres.postgres_timescale_bar_repository import (
                NullPostgresTimescaleBarRepository,
            )

            port = get_timescale_bar_port()
            if port is None or isinstance(port, NullPostgresTimescaleBarRepository):
                return self._apply_qfq_adjustment(rows, repo, stock_code)
            ts_rows = port.get_bars(
                symbol=stock_code, market="CN", adjust="qfq", limit=50000
            )
            by_date = _timescale_bars_to_history_rows(ts_rows)
            if not by_date:
                return self._apply_qfq_adjustment(rows, repo, stock_code)
            out: list[dict[str, Any]] = []
            for row in rows:
                ds = str(row["date"])[:10]
                if ds in by_date:
                    out.append(by_date[ds])
                else:
                    return self._apply_qfq_adjustment(rows, repo, stock_code)
            return out
        except Exception as exc:  # noqa: BLE001
            logger.debug("qlib bin timescale qfq fallback %s: %s", stock_code, exc)
            return self._apply_qfq_adjustment(rows, repo, stock_code)

    @staticmethod
    def _apply_qfq_adjustment(rows: list[dict[str, Any]], repo: Any, stock_code: str) -> list[dict[str, Any]]:
        """对原始 OHLCV 行应用前复权因子。"""
        factors = repo.fetch_factors_for_code(stock_code)
        if not factors:
            return rows
        factor_map = {str(f["date"]): float(f["factor"]) for f in factors}
        adjusted = []
        for row in rows:
            factor = factor_map.get(str(row["date"]), float(factors[-1]["factor"]))
            if factor <= 0:
                factor = 1.0
            r = dict(row)
            r["open"] = round(float(r["open"]) * factor, 2)
            r["high"] = round(float(r["high"]) * factor, 2)
            r["low"] = round(float(r["low"]) * factor, 2)
            r["close"] = round(float(r["close"]) * factor, 2)
            if factor > 0:
                r["volume"] = round(float(r["volume"]) / factor, 2)
                r["amount"] = round(float(r["amount"]) / factor, 2)
            adjusted.append(r)
        return adjusted

    def _write_stock_to_bin(self, code: str, rows: list, bin_dir, export_dir, features, date_to_idx, total_days, export_csv: bool):
        """将单只股票数据写入 bin 文件。

        目录结构：features/<stock_code>/<feature>.day.bin
        例如：features/sh600519/close.day.bin
        """
        import numpy as np

        qlib_code = code.lower()
        if not qlib_code.startswith(("sh", "sz", "bj")):
            prefix = "sh" if qlib_code.startswith("6") else "sz"
            qlib_code = f"{prefix}{qlib_code}"

        if export_csv:
            df = pd.DataFrame(rows)
            df.to_csv(export_dir / f"{qlib_code.upper()}.csv", index=False)

        # 股票代码目录，如 features/sh600519/
        stock_dir = bin_dir / "features" / qlib_code
        stock_dir.mkdir(parents=True, exist_ok=True)

        for feat in features:
            arr = np.full(total_days, np.nan, dtype=np.float32)
            for r in rows:
                d_str = str(r['date'])
                if d_str in date_to_idx:
                    arr[date_to_idx[d_str]] = float(r.get(feat) or 0)

            # 文件路径：features/sh600519/close.day.bin
            feat_path = stock_dir / f"{feat}.day.bin"
            with open(feat_path, "wb") as fb:
                fb.write(arr.tobytes())