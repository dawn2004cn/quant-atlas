from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""通达信基础数据入库：股票名称/基础列表、板块与成分股、财务快照等。"""


from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from app.config import AppSettings, get_settings
from app.core.logger import get_logger
from app.modules.system.services.helpers.tdx_data_repository_access import require_tdx_base_data_write_port
from app.modules.system.services.helpers.tdx_local_access import get_tdx_local_file_port
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.tdx_paths import TdxLocalPaths, resolve_tdx_root
from app.modules.system.services.helpers.tdx_finance_access import fetch_tdx_finance_snapshot

logger = get_logger(__name__)


class SyncMode(str, Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class ConflictStrategy(str, Enum):
    SKIP_EXISTS = "skip"
    OVERWRITE = "overwrite"
    MERGE = "merge"


def _now_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


@dataclass(frozen=True)
class TdxBaseIngestResult:
    ok: bool
    tdx_root: str
    stocks_upserted: int
    blocks_upserted: int
    block_items_upserted: int
    watchlists_upserted: int
    watchlist_items_upserted: int
    watchlist_items_added: int
    watchlist_items_skipped: int
    finance_upserted: int
    finance_failed: int
    at: str

    def to_dict(self) -> GenericResponseDTO:
        return {
            "ok": self.ok,
            "tdx_root": self.tdx_root,
            "stocks_upserted": self.stocks_upserted,
            "blocks_upserted": self.blocks_upserted,
            "block_items_upserted": self.block_items_upserted,
            "watchlists_upserted": self.watchlists_upserted,
            "watchlist_items_upserted": self.watchlist_items_upserted,
            "watchlist_items_added": self.watchlist_items_added,
            "watchlist_items_skipped": self.watchlist_items_skipped,
            "finance_upserted": self.finance_upserted,
            "finance_failed": self.finance_failed,
            "at": self.at,
        }


class TdxBaseDataService:
    """将通达信本地可用的“基础数据”统一落 MySQL。"""

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._tdx_root = resolve_tdx_root(self._settings.tdx_root_path)

    def ingest_all_to_mysql(
        self,
        *,
        ingest_finance: bool = False,
        ingest_watchlists: bool = False,
        finance_max_symbols: int | None = None,
        watchlist_sync_mode: SyncMode = SyncMode.INCREMENTAL,
        watchlist_conflict_strategy: ConflictStrategy = ConflictStrategy.MERGE,
    ) -> GenericResponseDTO:
        if not self._settings.use_mysql or self._settings.mysql is None:
            return {"ok": False, "error": "mysql_not_enabled"}
        if self._tdx_root is None:
            return {"ok": False, "error": "tdx_root_not_set"}

        paths = TdxLocalPaths(self._tdx_root)
        hq = paths.hq_cache
        tdx_port = get_tdx_local_file_port()

        basics = tdx_port.read_all_tnf_from_hq_cache(hq)
        blocks = tdx_port.read_all_block_dats(hq)
        logger.info(
            "tdx_base_ingest: parsed basics=%s blocks_items=%s (before mysql)",
            len(basics),
            len(blocks),
        )

        ts = _now_ts()
        basics_rows: list[tuple[str, str, str, str, str]] = []
        for b in basics:
            sym = SymbolNormalizer.to_db_code(b.cn_symbol, market="CN")
            mkt = sym[:2] if sym.startswith(("sh", "sz", "bj")) else "sh"
            basics_rows.append((sym, b.name, mkt, ts, "tdx_tnf"))

        block_item_rows: list[tuple[str, str, str, str]] = []
        for it in blocks:
            sym = SymbolNormalizer.to_db_code(it.cn_symbol, market="CN")
            block_item_rows.append((it.block_kind, it.block_name, sym, ts))

        watchlists = []
        if ingest_watchlists and self._settings.tdx_watchlist_ingest_enabled:
            extra_paths: list[Path] = []
            raw_paths = (self._settings.tdx_watchlist_paths or "").strip()
            if raw_paths:
                for part in raw_paths.replace(";", ",").split(","):
                    p = (part or "").strip()
                    if not p:
                        continue
                    extra_paths.append(Path(p))
            watchlists = get_tdx_local_file_port().read_tdx_blk_watchlists(
                tdx_root=self._tdx_root,
                extra_paths=extra_paths,
            )
            logger.info("tdx_watchlists_ingest: parsed watchlists=%s", len(watchlists))

        counts = require_tdx_base_data_write_port().ingest_base_data(
            basics=basics_rows,
            block_items=block_item_rows,
            ts=ts,
            ingest_watchlists=bool(ingest_watchlists and self._settings.tdx_watchlist_ingest_enabled),
            watchlists=watchlists,
            watchlist_sync_mode=watchlist_sync_mode.value,
            watchlist_conflict_strategy=watchlist_conflict_strategy.value,
            ingest_finance=bool(ingest_finance and self._settings.tdx_finance_ingest_enabled),
            finance_fetcher=fetch_tdx_finance_snapshot if ingest_finance else None,
            finance_max_symbols=(
                finance_max_symbols
                if finance_max_symbols is not None
                else self._settings.tdx_finance_max_symbols_per_run
            ),
            finance_rate_limit_rps=int(self._settings.tdx_finance_rate_limit_rps or 1),
        )
        logger.info(
            "tdx_base_ingest: mysql upserted stocks=%s blocks=%s block_items=%s",
            counts["stocks_upserted"],
            counts["blocks_upserted"],
            counts["block_items_upserted"],
        )
        out = TdxBaseIngestResult(
            ok=True,
            tdx_root=str(self._tdx_root),
            stocks_upserted=counts["stocks_upserted"],
            blocks_upserted=counts["blocks_upserted"],
            block_items_upserted=counts["block_items_upserted"],
            watchlists_upserted=counts["watchlists_upserted"],
            watchlist_items_upserted=counts["watchlist_items_upserted"],
            watchlist_items_added=counts["watchlist_items_added"],
            watchlist_items_skipped=counts["watchlist_items_skipped"],
            finance_upserted=counts["finance_upserted"],
            finance_failed=counts["finance_failed"],
            at=_now_ts(),
        )
        return out.to_dict()

