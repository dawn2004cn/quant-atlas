from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""通达信日 K（vipdoc/*/lday/*.day）→ MySQL + qlib_export(CSV) + qlib_bin 同步。

优化版本：
- 枚举所有 lday 文件（不依赖 MySQL 已有股票）
- 批量查询最新日期（解决 N+1 问题）
- 统一 stock_code 格式 (sh600519，无 CN: 前缀)
- 基于 xdxr 的正确复权因子计算
- 前后复权计算
- 每只股票独立提交（避免单点失败回滚批量数据）
- 增量补全缺失数据
- Qlib bin 自动导出
"""


from pathlib import Path
from typing import Any, Callable

from app.config import BASE_DIR, AppSettings
from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_bool, get_runtime_int
from app.modules.system.services.helpers.tdx_data_repository_access import require_tdx_dayk_write_port
from app.modules.data.services.qlib_pipeline_service import QlibPipelineService
from app.domain.dto.sync_dto import TdxSyncStatsDTO
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.tdx_paths import resolve_tdx_root

from app.modules.data.services.tdx_dayk_adjustment import (
    apply_backward_adjustment,
    apply_forward_adjustment,
    calculate_adjustment_factors,
)
from app.modules.data.services.tdx_dayk_csv_writer import write_qlib_csv
from app.modules.data.services.tdx_dayk_sync_helpers import (
    cap_mysql_sync_workers,
    cap_timescale_sync_workers,
    is_transient_conn_error,
    normalize_ohlcv_rows,
    qlib_instrument_for,
    scan_cn_codes_from_tdx_dayk,
)
from app.modules.data.services.tdx_dayk_sync_models import (
    SyncResult,
    SyncStatus,
    default_enable_timescale as _default_enable_timescale,
)
from app.modules.data.services.tdx_dayk_sync_runner import run_tdx_dayk_sync, sync_one_stock
from app.modules.data.services.tdx_dayk_timescale_writer import (
    apply_timescale_counts,
    open_timescale_sync_session,
    persist_timescale_package,
    refresh_timescale_matviews,
)

logger = get_logger(__name__)


class TdxDaykSyncService:
    """通达信日 K 线数据同步服务 - 优化版本."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        qlib_pipeline: QlibPipelineService,
        base_dir: Path = BASE_DIR,
    ) -> None:
        self._base = Path(base_dir)
        self._settings = settings
        self._qlib = qlib_pipeline
        self._tdx_root = resolve_tdx_root(self._settings.tdx_root_path)

    def _require_tdx_root(self) -> Path:
        if self._tdx_root is None:
            raise ValueError("TDX_ROOT_PATH not configured")
        return self._tdx_root

    scan_cn_codes_from_tdx_dayk = staticmethod(scan_cn_codes_from_tdx_dayk)

    @staticmethod
    def _normalize_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return normalize_ohlcv_rows(rows)

    def _calculate_adjustment_factors(
        self, raw_rows: list[dict[str, Any]], market: str, code: str
    ) -> list[dict[str, Any]]:
        return calculate_adjustment_factors(raw_rows, market, code)

    def _apply_forward_adjustment(
        self, rows: list[dict[str, Any]], factors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return apply_forward_adjustment(rows, factors)

    def _apply_backward_adjustment(
        self, rows: list[dict[str, Any]], factors: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return apply_backward_adjustment(rows, factors)

    def _write_csv(
        self, cn_symbol: str, rows: list[dict[str, Any]], merge: bool = False
    ) -> tuple[int, str, str]:
        return write_qlib_csv(
            Path(self._qlib.export_dir),
            self._get_qlib_instrument(cn_symbol),
            rows,
            merge=merge,
        )

    def _open_timescale_sync_session(self) -> Any | None:
        return open_timescale_sync_session()

    def _persist_timescale_package(
        self,
        stock_code: str,
        raw_rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
        *,
        ts_session: Any | None = None,
    ) -> dict[str, int]:
        return persist_timescale_package(
            self._settings,
            stock_code,
            raw_rows,
            factors,
            ts_session=ts_session,
        )

    _cap_mysql_sync_workers = staticmethod(cap_mysql_sync_workers)
    _cap_timescale_sync_workers = staticmethod(cap_timescale_sync_workers)
    _is_transient_conn_error = staticmethod(is_transient_conn_error)

    def _refresh_timescale_matviews(self) -> None:
        refresh_timescale_matviews(self._settings)

    def _apply_timescale_counts(self, result: SyncResult, counts: dict[str, int]) -> None:
        apply_timescale_counts(result, counts)

    @staticmethod
    def _lday_tail_for_sync(mode: str, latest: str | None) -> int | None:
        """增量/日更且库内已有最新日时，仅读 lday 尾部以降低 IO。"""
        from app.modules.data.services.ohlcv_incremental_policy import tdx_lday_tail_bars

        return tdx_lday_tail_bars(mode, latest)

    def _sync_one_stock(
        self,
        cn_symbol: str,
        raw_rows: list[dict[str, Any]],
        mysql_session,
        csv_merge: bool,
        *,
        ts_session: Any | None = None,
        enable_csv: bool = True,
        enable_timescale: bool = False,
    ) -> SyncResult:
        return sync_one_stock(
            cn_symbol=cn_symbol,
            raw_rows=raw_rows,
            mysql_session=mysql_session,
            csv_merge=csv_merge,
            settings=self._settings,
            export_dir=self._qlib.export_dir,
            ts_session=ts_session,
            enable_csv=enable_csv,
            enable_timescale=enable_timescale,
        )

    def _run_sync(
        self,
        mode: str,
        codes: list[str],
        filter_rows: Callable,
        csv_merge: bool,
        dump_qlib_bin: bool,
        dump_max_workers: int,
        start_date: str | None = None,
        adjust_type: str = "forward",
        skip_latest_dates: bool = False,
        *,
        mysql_table_suffix: str = "",
        mysql_insert_only: bool = False,
        enable_csv: bool = True,
        enable_timescale: bool | None = None,
        enable_mysql: bool | None = None,
        write_checkpoint: bool = True,
    ) -> GenericResponseDTO:
        return run_tdx_dayk_sync(
            self,
            mode,
            codes,
            filter_rows,
            csv_merge,
            dump_qlib_bin,
            dump_max_workers,
            start_date=start_date,
            adjust_type=adjust_type,
            skip_latest_dates=skip_latest_dates,
            mysql_table_suffix=mysql_table_suffix,
            mysql_insert_only=mysql_insert_only,
            enable_csv=enable_csv,
            enable_timescale=enable_timescale,
            enable_mysql=enable_mysql,
            write_checkpoint=write_checkpoint,
        )

    def _get_qlib_instrument(self, cn_symbol: str) -> str:
        return qlib_instrument_for(cn_symbol)

    def retry_failed_from_tdx(
        self,
        *,
        failed_file: Path | str | None = None,
        workers: int | None = None,
        mysql_table_suffix: str = "_new",
        dump_qlib_bin: bool = False,
        enable_csv: bool = True,
        enable_timescale: bool = False,
    ) -> GenericResponseDTO:
        """仅重跑检查点中的失败代码（UPSERT 续传，不清空 ``*_new``）。"""
        from app.modules.data.services.tdx_sync_checkpoint import load_failed_codes
        from app.infrastructure.database.mysql_client import dispose_mysql_engines

        dispose_mysql_engines(self._settings.mysql)
        codes = load_failed_codes(file=failed_file)
        if not codes:
            return {
                "ok": True,
                "mode": "retry_failed",
                "message": "no failed codes in checkpoint",
                "stats": {},
            }

        worker_n = self._cap_mysql_sync_workers(
            workers or get_runtime_int("TDX_MYSQL_SYNC_WORKERS", 3)
        )
        logger.info("Retry %d failed symbols from checkpoint", len(codes))
        result = self._run_sync(
            mode="retry_failed",
            codes=codes,
            filter_rows=lambda rows, latest: rows,
            csv_merge=False,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=worker_n,
            skip_latest_dates=True,
            mysql_table_suffix=mysql_table_suffix,
            mysql_insert_only=False,
            enable_csv=enable_csv,
            enable_timescale=enable_timescale,
        )
        out: dict[str, Any] = dict(result)
        out["retry_input_count"] = len(codes)
        return out

    def full_sync_all_from_tdx(
        self,
        *,
        limit: int | None = None,
        workers: int | None = None,
        mysql_table_suffix: str = "_new",
        swap_mysql_tables: bool = False,
        truncate_factors: bool = False,
        dump_qlib_bin: bool = True,
        resume_skip_ok: bool = False,
        clear_checkpoint: bool = False,
    ) -> GenericResponseDTO:
        """一次全量：TDX lday+xdxr → MySQL 分表 + ``stock_adjustment_factor`` + Timescale + CSV + qlib_bin。

        写入 ``*_new`` 时默认先不 dump bin，``swap_mysql_tables`` 后再从生产 MySQL 导 bin。
        ``resume_skip_ok``：跳过 ``instance/tdx_sync/ok_codes.txt`` 中已成功代码。
        """
        from app.infrastructure.repositories.mysql.mysql_tdx_dayk_repository import (
            MySQLTdxDaykRepository,
        )

        if not self._settings.use_mysql:
            raise ValueError("use_mysql required for full_sync_all_from_tdx")

        from app.modules.data.services.tdx_sync_checkpoint import (
            checkpoint_dir,
            filter_codes_resume,
        )
        from app.infrastructure.database.mysql_client import dispose_mysql_engines

        dispose_mysql_engines(self._settings.mysql)

        if clear_checkpoint:
            import shutil

            d = checkpoint_dir()
            if d.is_dir():
                shutil.rmtree(d)

        worker_n = self._cap_mysql_sync_workers(
            workers or get_runtime_int("TDX_FULL_SYNC_WORKERS", 3)
        )
        insert_only = bool(mysql_table_suffix) and get_runtime_bool(
            "TDX_MYSQL_INSERT_ONLY", False
        )
        defer_bin = bool(mysql_table_suffix)

        port = require_tdx_dayk_write_port()
        if mysql_table_suffix and get_runtime_bool("TDX_MYSQL_TRUNCATE_SUFFIX_TABLES", True):
            if hasattr(port, "truncate_history_tables"):
                port.truncate_history_tables(mysql_table_suffix)
        if truncate_factors and hasattr(port, "truncate_adjustment_factors"):
            port.truncate_adjustment_factors()

        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if resume_skip_ok:
            before = len(codes)
            codes = filter_codes_resume(codes)
            logger.info("Resume: %d -> %d symbols (skipped %d ok in checkpoint)", before, len(codes), before - len(codes))
        if limit:
            codes = codes[:limit]

        result = self._run_sync(
            mode="full",
            codes=codes,
            filter_rows=lambda rows, latest: rows,
            csv_merge=False,
            dump_qlib_bin=dump_qlib_bin and not defer_bin,
            dump_max_workers=worker_n,
            skip_latest_dates=True,
            mysql_table_suffix=mysql_table_suffix,
            mysql_insert_only=insert_only,
            enable_csv=True,
            enable_timescale=_default_enable_timescale(),
        )

        out: dict[str, Any] = dict(result)
        out["targets"] = {
            "mysql_tables": [
                f"stock_history_sh{mysql_table_suffix}",
                f"stock_history_sz{mysql_table_suffix}",
                f"stock_history_bj{mysql_table_suffix}",
            ],
            "adjustment_factor": "stock_adjustment_factor",
            "timescale": bool(self._settings.use_timescaledb),
            "csv": str(self._qlib.export_dir),
            "qlib_bin": dump_qlib_bin,
        }

        if swap_mysql_tables:
            if not mysql_table_suffix:
                raise ValueError("swap_mysql_tables requires mysql_table_suffix (e.g. _new)")
            if int(result.get("failed") or 0) > 0:
                raise RuntimeError(
                    f"refusing table swap: {result.get('failed')} symbols failed; "
                    "run with --retry-failed until failed=0"
                )
            MySQLTdxDaykRepository.swap_reload_tables(mysql_table_suffix)
            out["mysql_swapped"] = True

        if dump_qlib_bin and defer_bin:
            try:
                bin_res = self._qlib.dump_to_qlib_bin(incremental=False)
                out["qlib_bin"] = bin_res
                logger.info("qlib_bin dumped after MySQL swap")
            except Exception as exc:
                logger.warning("qlib_bin dump failed: %s", exc)
                out["qlib_bin_error"] = str(exc)

        return out

    def reload_mysql_history_from_tdx(
        self,
        *,
        table_suffix: str = "_new",
        limit: int | None = None,
        mysql_workers: int | None = None,
        write_timescale: bool = False,
        write_csv: bool = False,
        dump_qlib_bin: bool = False,
    ) -> GenericResponseDTO:
        """重灌 MySQL 日 K 分表（TDX lday + xdxr），默认写入 ``stock_history_*_new``。"""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if limit:
            codes = codes[:limit]
        from app.infrastructure.database.mysql_client import dispose_mysql_engines

        dispose_mysql_engines(self._settings.mysql)
        worker_n = self._cap_mysql_sync_workers(
            mysql_workers or get_runtime_int("TDX_MYSQL_SYNC_WORKERS", 3)
        )
        insert_only = get_runtime_bool("TDX_MYSQL_INSERT_ONLY", False) and bool(table_suffix)

        port = require_tdx_dayk_write_port()
        if table_suffix and get_runtime_bool("TDX_MYSQL_TRUNCATE_SUFFIX_TABLES", False):
            if hasattr(port, "truncate_history_tables"):
                port.truncate_history_tables(table_suffix)

        def filter_all(rows, latest):
            return rows

        return self._run_sync(
            mode="full",
            codes=codes,
            filter_rows=filter_all,
            csv_merge=False,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=worker_n,
            skip_latest_dates=True,
            mysql_table_suffix=table_suffix,
            mysql_insert_only=insert_only,
            enable_csv=write_csv,
            enable_timescale=write_timescale,
        )

    def timescale_full_sync_from_tdx_dayk(
        self,
        limit: int | None = None,
        offset: int = 0,
        dump_max_workers: int = 4,
    ) -> GenericResponseDTO:
        """仅 TDX → Timescale（独立任务，不写 MySQL/CSV）。"""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        eff_limit = None if limit is not None and limit <= 0 else limit
        end = offset + eff_limit if eff_limit is not None else None
        # 分页 backfill（limit/offset）在全市场列表上切片；勿先 filter ok_codes 再 offset（会误判已完成）
        if get_runtime_bool("TIMESCALE_RESUME_OK_CODES", True) and eff_limit is None and offset == 0:
            from app.modules.data.services.tdx_sync_checkpoint import filter_codes_resume

            codes = filter_codes_resume(codes)
        else:
            codes = codes[offset:end]

        def filter_all(rows, latest):
            return rows

        return self._run_sync(
            mode="full",
            codes=codes,
            filter_rows=filter_all,
            csv_merge=False,
            dump_qlib_bin=False,
            dump_max_workers=dump_max_workers,
            skip_latest_dates=True,
            enable_csv=False,
            enable_timescale=True,
            enable_mysql=False,
            write_checkpoint=get_runtime_bool("TIMESCALE_SYNC_CHECKPOINT", True),
        )

    def timescale_sync_codes_from_tdx_dayk(
        self,
        symbols: list[str],
        dump_max_workers: int = 1,
    ) -> GenericResponseDTO:
        """按指定标的列表写入 Timescale（用于失败代码补跑）。"""
        codes = [SymbolNormalizer.normalize_cn_symbol(s) for s in symbols if str(s).strip()]
        if not codes:
            return {
                "ok": False,
                "error": "no_symbols",
                "stats": TdxSyncStatsDTO(
                    codes_total=0,
                    codes_ok=0,
                    mysql_rows=0,
                    csv_written=0,
                    date_min="",
                    date_max="",
                ).model_dump(),
            }

        def filter_all(rows, latest):
            return rows

        return self._run_sync(
            mode="full",
            codes=codes,
            filter_rows=filter_all,
            csv_merge=False,
            dump_qlib_bin=False,
            dump_max_workers=dump_max_workers,
            skip_latest_dates=True,
            enable_csv=False,
            enable_timescale=True,
            enable_mysql=False,
            write_checkpoint=get_runtime_bool("TIMESCALE_SYNC_CHECKPOINT", True),
        )

    def full_sync_from_tdx_dayk(
        self,
        limit: int | None = None,
        dump_qlib_bin: bool = True,
        dump_max_workers: int = 8,
        csv_merge: bool = False,
        adjust_type: str = "forward",
        *,
        enable_timescale: bool | None = None,
        enable_csv: bool | None = None,
        enable_mysql: bool | None = None,
    ) -> GenericResponseDTO:
        """全量同步 TDX dayk → MySQL/CSV/qlib（默认不写 Timescale）。"""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if limit:
            codes = codes[:limit]

        def filter_all(rows, latest):
            return rows

        return self._run_sync(
            mode="full",
            codes=codes,
            filter_rows=filter_all,
            csv_merge=csv_merge,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
            adjust_type=adjust_type,
            skip_latest_dates=True,
            enable_timescale=enable_timescale,
            enable_csv=enable_csv,
            enable_mysql=enable_mysql,
        )

    def daily_sync_from_tdx_dayk(
        self,
        trade_date: str | None = None,
        limit: int | None = None,
        dump_qlib_bin: bool = True,
        dump_max_workers: int = 8,
        adjust_type: str = "forward",
    ) -> GenericResponseDTO:
        """每日同步指定交易日数据."""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if limit:
            codes = codes[:limit]

        def filter_by_date(rows, latest):
            if trade_date:
                return [r for r in rows if r.get("date", "").startswith(trade_date)]
            if latest:
                return [r for r in rows if r.get("date", "") > latest]
            return rows

        return self._run_sync(
            mode="daily",
            codes=codes,
            filter_rows=filter_by_date,
            csv_merge=True,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
            adjust_type=adjust_type,
        )

    def incremental_sync_from_tdx_dayk(
        self,
        start_date: str | None = None,
        trade_date: str | None = None,
        limit: int | None = None,
        dump_qlib_bin: bool = False,
        dump_max_workers: int = 8,
        adjust_type: str = "forward",
        backfill_missing: bool = True,
        *,
        enable_timescale: bool | None = None,
        enable_csv: bool | None = None,
        enable_mysql: bool | None = None,
    ) -> GenericResponseDTO:
        """增量同步 TDX dayk（默认 MySQL 增量；Timescale 请用 ``timescale_full_sync`` / 独立任务）。"""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if limit:
            codes = codes[:limit]

        sd = start_date
        if not sd and trade_date:
            sd = trade_date

        from app.modules.data.services.ohlcv_incremental_policy import make_incremental_row_filter

        return self._run_sync(
            mode="incremental",
            codes=codes,
            filter_rows=make_incremental_row_filter(),
            csv_merge=True,
            dump_qlib_bin=dump_qlib_bin,
            dump_max_workers=dump_max_workers,
            start_date=sd,
            adjust_type=adjust_type,
            enable_timescale=enable_timescale,
            enable_csv=enable_csv,
            enable_mysql=enable_mysql,
        )

    def backfill_missing_data(
        self,
        limit: int | None = None,
        adjust_type: str = "forward",
    ) -> GenericResponseDTO:
        """补全缺失的历史数据（全量重写确保数据一致性）."""
        codes = self.scan_cn_codes_from_tdx_dayk(self._require_tdx_root())
        if limit:
            codes = codes[:limit]

        def filter_all(rows, latest):
            return rows

        return self._run_sync(
            mode="backfill",
            codes=codes,
            filter_rows=filter_all,
            csv_merge=True,
            dump_qlib_bin=True,
            dump_max_workers=8,
            adjust_type=adjust_type,
        )

