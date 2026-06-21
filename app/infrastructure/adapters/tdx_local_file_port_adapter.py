from __future__ import annotations
"""Infrastructure adapter for ``TdxLocalFilePort``."""

from pathlib import Path
from typing import Any

from app.domain.ports.market_ports import HistoryPort
from app.domain.ports.tdx_local_port import TdxLocalFilePort
from app.infrastructure.providers.tdx_file_adapter import (
    TDXFileHistoryAdapter,
    TDXFileHistoryWithOptimization,
)
from app.infrastructure.tdx_local.block_dat_reader import read_all_block_dats
from app.infrastructure.tdx_local.lday_reader import fetch_xdxr_data, read_lday_file
from app.infrastructure.tdx_local.qfq_calculator import (
    apply_qfq_to_rows,
    compute_qfq_factors_from_xdxr,
)
from app.infrastructure.tdx_local.tdx_blocks import list_blocks_for_code
from app.infrastructure.tdx_local.tdx_gbbq import gbbq_rows_for_code
from app.infrastructure.tdx_local.tnf_reader import read_all_tnf_from_hq_cache
from app.infrastructure.tdx_local.watchlist_reader import read_tdx_blk_watchlists


class TdxLocalFilePortAdapter(TdxLocalFilePort):
    """Delegates to existing ``tdx_local`` readers and file history adapters."""

    def read_lday_file(self, path: Path, *, tail: int | None = None) -> list[dict[str, Any]]:
        return read_lday_file(path, tail=tail)

    def fetch_xdxr_data(self, market: str, code: str) -> Any:
        return fetch_xdxr_data(market, code)

    def compute_qfq_factors_from_xdxr(
        self,
        raw_rows: list[dict[str, Any]],
        df_xdxr: Any,
    ) -> list[dict[str, Any]]:
        return compute_qfq_factors_from_xdxr(raw_rows, df_xdxr)

    def apply_qfq_to_rows(
        self,
        rows: list[dict[str, Any]],
        factors: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return apply_qfq_to_rows(rows, factors)

    def read_all_tnf_from_hq_cache(self, hq_cache: Path) -> list[Any]:
        return read_all_tnf_from_hq_cache(hq_cache)

    def read_all_block_dats(self, hq_cache: Path) -> list[Any]:
        return read_all_block_dats(hq_cache)

    def read_tdx_blk_watchlists(
        self,
        *,
        tdx_root: Path,
        extra_paths: list[Path] | None = None,
    ) -> list[Any]:
        return read_tdx_blk_watchlists(tdx_root=tdx_root, extra_paths=extra_paths)

    def list_blocks_for_code(
        self,
        hq_cache: Path,
        code6: str,
        *,
        max_block_names: int = 24,
    ) -> tuple[list[str], str]:
        return list_blocks_for_code(hq_cache, code6, max_block_names=max_block_names)

    def gbbq_rows_for_code(
        self,
        gbbq_path: Path,
        code6: str,
        *,
        tail: int = 15,
    ) -> tuple[list[dict[str, Any]], str]:
        return gbbq_rows_for_code(gbbq_path, code6, tail=tail)

    def create_history_adapter(self, tdx_root_path: str | None) -> HistoryPort | None:
        if not tdx_root_path:
            return None
        return TDXFileHistoryAdapter(tdx_root_path)

    def create_optimized_history(
        self,
        tdx_root_path: str,
        *,
        use_arrow: bool = True,
    ) -> Any | None:
        return TDXFileHistoryWithOptimization(tdx_root_path, use_arrow=use_arrow)
