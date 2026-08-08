from __future__ import annotations

"""Read-only TDX base data queries via TdxBlockReadPort."""

from typing import Any

from app.application.errors import ValidationError
from app.modules.system.services.helpers.tdx_block_repository_access import require_tdx_block_read_port
from app.config import AppSettings, get_settings
from app.core.registry import register_service
from app.domain.shared.symbol_normalizer import SymbolNormalizer


@register_service(name="tdx_base_read_service")
class TdxBaseReadService:
    """MySQL-backed TDX blocks / watchlists / finance read paths for API routes."""

    def __init__(self, *, settings: AppSettings | None = None) -> None:
        self._settings = settings or get_settings()

    def _require_port(self):
        if not self._settings.use_mysql or self._settings.mysql is None:
            raise ValidationError("mysql_not_enabled")
        port = require_tdx_block_read_port()
        if port is None:
            raise ValidationError("tdx_block_repository_unavailable")
        return port

    def list_blocks(self, *, block_kind: str | None = None) -> list[dict[str, Any]]:
        return self._require_port().list_blocks_simple(block_kind=block_kind)

    def list_block_members(
        self,
        *,
        block_kind: str,
        block_name: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        port = self._require_port()
        key = (block_kind.strip().lower(), block_name.strip())
        grouped = port.load_members_bulk([key], per_block_limit=max(1, limit))
        return grouped.get(key, [])

    def list_symbol_blocks(self, symbol: str) -> list[dict[str, Any]]:
        raw = (symbol or "").strip()
        if not raw:
            raise ValidationError("symbol is required")
        sym = SymbolNormalizer.to_db_code(raw, market="CN")
        code6 = SymbolNormalizer.normalize_code(sym)
        lookup = tuple({sym, code6, f"CN:{sym}", f"CN:{code6}"})
        return self._require_port().list_symbol_blocks(list(lookup))

    def list_watchlists(self) -> list[dict[str, Any]]:
        return self._require_port().list_watchlists()

    def list_watchlist_members(self, *, watchlist_name: str) -> list[dict[str, Any]]:
        name = (watchlist_name or "").strip()
        if not name:
            raise ValidationError("name is required")
        return self._require_port().list_watchlist_members(watchlist_name=name)

    def get_latest_finance_snapshot(self, symbol: str) -> dict[str, Any] | None:
        raw = (symbol or "").strip()
        if not raw:
            raise ValidationError("symbol is required")
        sym = SymbolNormalizer.to_db_code(raw, market="CN")
        return self._require_port().get_latest_finance_snapshot(sym)
