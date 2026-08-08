from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""通达信板块成分股内存索引（避免 summaries 接口重复慢 SQL）。"""


import threading
import time
from typing import Any

from app.application.errors import ValidationError
from app.config import get_settings
from app.core.logger import get_logger
from app.modules.system.services.helpers.tdx_block_repository_access import (
    get_tdx_block_read_port,
    require_tdx_block_read_port,
)

logger = get_logger(__name__)

_CACHE_TTL_SEC = 300


class TdxBlockMembershipCache:
    """按 block_kind 缓存 symbol 列表；names 由行情快照补齐。"""

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()
        self._lock = threading.RLock()
        # kind -> (loaded_at, {(kind,name): [symbols]})
        self._by_kind: dict[str, tuple[float, dict[tuple[str, str], list[str]]]] = {}

    def members_for_blocks(
        self,
        block_keys: list[tuple[str, str]],
        *,
        per_block_limit: int,
        block_kind: str = "",
    ) -> GenericResponseDTO[tuple[str, str], list[dict[str, str]]]:
        if not block_keys:
            return {}
        index = self._index_for_kind(block_kind)
        out: dict[tuple[str, str], list[dict[str, str]]] = {}
        for key in block_keys:
            syms = index.get(key, [])[:per_block_limit]
            out[key] = [{"symbol": s, "name": ""} for s in syms]
        return out

    def symbols_for_block(
        self, block_kind: str, block_name: str, *, limit: int
    ) -> list[dict[str, str]]:
        key = (str(block_kind or "").strip().lower(), str(block_name or "").strip())
        index = self._index_for_kind(block_kind)
        syms = index.get(key, [])[:limit]
        return [{"symbol": s, "name": ""} for s in syms]

    def _index_for_kind(self, block_kind: str) -> GenericResponseDTO[tuple[str, str], list[str]]:
        kind = (block_kind or "").strip().lower() or "__all__"
        now = time.time()
        with self._lock:
            loaded = self._by_kind.get(kind)
            if loaded and now - loaded[0] < _CACHE_TTL_SEC:
                return loaded[1]
            index = self._load_from_mysql(kind if kind != "__all__" else "")
            self._by_kind[kind] = (now, index)
            logger.info("TdxBlockMembershipCache loaded kind=%s blocks=%s", kind, len(index))
            return index

    def _load_from_mysql(self, block_kind: str) -> GenericResponseDTO[tuple[str, str], list[str]]:
        settings = self._settings
        if not settings.use_mysql or settings.mysql is None:
            raise ValidationError("mysql_not_enabled")
        repo = get_tdx_block_read_port()
        if repo is None:
            raise ValidationError("tdx_block_repository_unavailable")
        return repo.load_membership_index(block_kind)

    def invalidate(self, block_kind: str = "") -> None:
        with self._lock:
            if block_kind:
                self._by_kind.pop(block_kind.strip().lower(), None)
            else:
                self._by_kind.clear()


_membership_cache: TdxBlockMembershipCache | None = None
_cache_lock = threading.Lock()


def get_tdx_block_membership_cache() -> TdxBlockMembershipCache:
    global _membership_cache
    if _membership_cache is None:
        with _cache_lock:
            if _membership_cache is None:
                _membership_cache = TdxBlockMembershipCache()
    return _membership_cache
