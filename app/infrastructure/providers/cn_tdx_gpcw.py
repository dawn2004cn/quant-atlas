from __future__ import annotations
"""TDX 本地专业财务数据文件 (gpcw*.dat) 读取器与 Provider。

文件格式（pytdx 标准格式）：
- 20 字节头: <1hI1H3L → (ver, report_date, max_count, L1, report_size, L3)
- 11 字节索引项: <6s1c1L → (code, unk, offset)
- 数据区: 每只股票 float[report_fields_count]

文件从 http://down.tdx.com.cn:8001/tdxfin/ 下载（gpcw{yyyyMMdd}.zip）
本地目录: vipdoc/cw/gpcw*.dat

字段含义: 见 cn_tdx_gpcw_fields.GPCW_FIELD_NAMES (1-indexed, 1-584)
"""


from pathlib import Path
from typing import Any

import pandas as pd
from struct import unpack, calcsize
from .cn_tdx_gpcw_fields import GPCW_FIELD_NAMES
from ..tdx_local.paths import TdxLocalPaths, resolve_tdx_root

from app.core.logger import get_logger

logger = get_logger(__name__)

_HDR_FMT = "<1hI1H3L"
_TDX_GPCW_FIELD_COUNT = 584


def _parse_header(fp: Path) -> tuple[int, int, int] | None:
    try:
        with open(fp, "rb") as f:
            hdr = unpack(_HDR_FMT, f.read(calcsize(_HDR_FMT)))
        return hdr[1], hdr[2], hdr[4]  # report_date, max_count, report_size
    except Exception:
        return None


class CnTdxGpcwProvider:
    _header_cache: dict[str, tuple[int, int]] = {}

    def __init__(self, tdx_root_path: str | None = None) -> None:
        self._tdx_root = resolve_tdx_root(tdx_root_path)

    @property
    def gpcw_dir(self) -> Path | None:
        if self._tdx_root is None:
            return None
        return TdxLocalPaths(self._tdx_root).gpcw_dir

    def _scan_dat_files(self, dir_path: Path) -> list[tuple[Path, int, int]]:
        files = []
        for fpath in sorted(dir_path.iterdir()):
            if fpath.suffix.lower() != ".dat":
                continue
            if not fpath.name.startswith("gpcw"):
                continue
            if fpath.stat().st_size < 1000:
                continue
            cached = self._header_cache.get(str(fpath))
            if cached:
                report_date, max_count = cached
            else:
                result = _parse_header(fpath)
                if result is None:
                    continue
                report_date, max_count, _ = result
                self._header_cache[str(fpath)] = (report_date, max_count)
            if max_count < 100:
                continue
            files.append((fpath, report_date, max_count))
        return files

    def _find_dat_file_for_stock(
        self, dir_path: Path, symbol: str
    ) -> tuple[Path, int, int] | None:
        """Find the latest dat file that contains the given stock."""
        from pytdx.reader import HistoryFinancialReader

        files = self._scan_dat_files(dir_path)
        files.sort(key=lambda x: x[1], reverse=True)
        code6 = symbol.strip()[-6:].lstrip("0")
        reader = HistoryFinancialReader()

        for fpath, report_date, max_count in files:
            if max_count < 500:
                continue
            try:
                df = reader.get_df(str(fpath))
                if df is not None and code6 in df.index:
                    return fpath, report_date, max_count
            except Exception:
                continue
        return None

    def get_latest_data(self, symbol: str, *, max_periods: int = 8) -> dict[str, Any]:
        dir_path = self.gpcw_dir
        if dir_path is None or not dir_path.is_dir():
            return {"ok": False, "error": "tdx_root_not_configured"}

        result = self._find_dat_file_for_stock(dir_path, symbol)
        if result is None:
            return {"ok": False, "error": "no_gpcw_dat_files_contain_stock"}

        dat_file, report_date, _ = result
        return self._get_stock_data_from_file(symbol, dat_file, max_periods=max_periods)

    def _get_stock_data_from_file(
        self, symbol: str, dat_file: Path, *, max_periods: int = 1
    ) -> dict[str, Any]:
        from pytdx.reader import HistoryFinancialReader

        try:
            reader = HistoryFinancialReader()
            df = reader.get_df(str(dat_file))
            if df is None or df.empty:
                return {"ok": False, "error": "reader_returned_empty"}
        except Exception as exc:
            logger.warning("Failed to read gpcw %s: %s", dat_file.name, exc)
            return {"ok": False, "error": str(exc)}

        code6 = symbol.strip()[-6:].lstrip("0")
        if code6 not in df.index:
            return {"ok": False, "error": f"stock {code6} not in {dat_file.name}"}

        row = df.loc[code6]
        report_date = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
        values = row.iloc[1 : _TDX_GPCW_FIELD_COUNT + 1].fillna(0).tolist()
        return {
            "ok": True,
            "file": dat_file.name,
            "report_date": report_date,
            "fields": values,
            "total_fields": len(values),
        }

    def get_named_fields(self, raw_values: list[float]) -> dict[str, float]:
        """将原始 584 字段值映射为具名 dict。"""
        result = {}
        for idx, val in enumerate(raw_values, start=1):
            name = GPCW_FIELD_NAMES.get(idx, f"field_{idx}")
            if abs(val) > 0.0001:
                result[name] = val
        return result

    def get_all_periods(self, symbol: str) -> list[dict[str, Any]]:
        dir_path = self.gpcw_dir
        if dir_path is None or not dir_path.is_dir():
            return []

        from pytdx.reader import HistoryFinancialReader

        files = self._scan_dat_files(dir_path)
        files.sort(key=lambda x: x[1], reverse=True)
        reader = HistoryFinancialReader()
        code6 = symbol.strip()[-6:].lstrip("0")

        results = []
        for fpath, report_date, max_count in files:
            if max_count < 500:
                continue
            try:
                df = reader.get_df(str(fpath))
                if df is None or code6 not in df.index:
                    continue
                row = df.loc[code6]
                rd = int(row.iloc[0]) if pd.notna(row.iloc[0]) else 0
                values = row.iloc[1 : _TDX_GPCW_FIELD_COUNT + 1].fillna(0).tolist()
                results.append({
                    "ok": True,
                    "file": fpath.name,
                    "report_date": rd,
                    "fields": values,
                    "total_fields": len(values),
                })
                if len(results) >= 26:
                    break
            except Exception:
                continue

        return results
