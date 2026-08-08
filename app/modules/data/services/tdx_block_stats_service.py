from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""通达信板块实时统计：涨幅、涨股比、龙头（基于成分股行情）??"""


from typing import Any

from app.application.errors import ValidationError
from app.config import get_settings
from app.core.logger import get_logger
from app.modules.data.services.cn_realtime_quote_service import CnRealtimeQuoteService
from app.modules.data.services.tdx_block_membership_cache import get_tdx_block_membership_cache
from app.modules.market_data.services.cn_quote_snapshot import get_cn_quote_snapshot
from app.modules.system.services.helpers.tdx_block_repository_access import require_tdx_block_read_port
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.shared.sector_board_metrics import aggregate_member_stats

logger = get_logger(__name__)

_MEMBERS_PER_BLOCK = 150
_SUMMARY_MEMBERS_PER_BLOCK = 48
_MAX_SUMMARY_SYMBOLS = 1200


class TdxBlockStatsService:
    """??MySQL 通达信板块成分基础上汇总行情指标（批量查库 + 批量行情）??"""

    def __init__(
        self,
        *,
        settings: AppSettings | None = None,
        market_provider: object | None = None,
        quote_service: CnRealtimeQuoteService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._market_provider = market_provider
        self._normalizer = SymbolNormalizer()
        self._quote_service = quote_service

    def _quotes(self) -> CnRealtimeQuoteService:
        if self._quote_service is None:
            self._quote_service = CnRealtimeQuoteService(
                market_provider=self._market_provider
            )
        return self._quote_service

    def _require_mysql(self):
        if not self._settings.use_mysql or self._settings.mysql is None:
            raise ValidationError("mysql_not_enabled")
        return self._settings.mysql

    @staticmethod
    def _block_key(kind: str, name: str) -> tuple[str, str]:
        return (str(kind or "").strip().lower(), str(name or "").strip())

    @staticmethod
    def _symbol_keys(symbol: str) -> list[str]:
        raw = str(symbol or "").strip()
        if not raw:
            return []
        norm = raw.split(":", 1)[1] if ":" in raw else raw
        keys = {raw, norm}
        if norm.lower().startswith(("sh", "sz", "bj")):
            keys.add(norm[2:])
        digits = "".join(ch for ch in norm if ch.isdigit())[-6:].zfill(6)
        if digits and digits != "000000":
            keys.add(digits)
        return list(keys)

    def list_block_summaries(
        self,
        *,
        block_kind: str = "",
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        """返回板块列表及汇总指标（按板块涨幅降序，单次批量行情）??"""
        cap = max(1, min(int(limit or 60), 120))
        blocks = self._load_blocks_meta(block_kind=block_kind, limit=cap)
        if not blocks:
            return []

        keys = [self._block_key(b["block_kind"], b["block_name"]) for b in blocks]
        members_by_block = get_tdx_block_membership_cache().members_for_blocks(
            keys,
            per_block_limit=_SUMMARY_MEMBERS_PER_BLOCK,
            block_kind=block_kind,
        )

        all_symbols: list[str] = []
        seen: set[str] = set()
        for members in members_by_block.values():
            for m in members:
                sym = m.get("symbol") or ""
                if sym and sym not in seen:
                    seen.add(sym)
                    all_symbols.append(sym)
                    if len(all_symbols) >= _MAX_SUMMARY_SYMBOLS:
                        break
            if len(all_symbols) >= _MAX_SUMMARY_SYMBOLS:
                break

        quotes = self._fetch_quotes(all_symbols)

        summaries: list[dict[str, Any]] = []
        for blk in blocks:
            key = self._block_key(blk["block_kind"], blk["block_name"])
            members = members_by_block.get(key, [])
            stats = self._aggregate_block(members, quotes)
            if blk.get("member_count_total"):
                stats["member_count"] = int(blk["member_count_total"])
            summaries.append(
                {
                    **blk,
                    **stats,
                    "source": "通达?",
                    "provider": "tdx",
                    "sector_code": f"{blk['block_kind']}:{blk['block_name']}",
                    "name": blk["block_name"],
                    "kind": blk["block_kind"],
                }
            )

        summaries.sort(key=lambda x: float(x.get("change_pct") or 0), reverse=True)
        return summaries[:cap]

    def block_summary(self, block_kind: str, block_name: str) -> GenericResponseDTO | None:
        """单板块汇总；无成分股时返回空指标??"""
        members = get_tdx_block_membership_cache().symbols_for_block(
            block_kind, block_name, limit=_MEMBERS_PER_BLOCK
        )
        quotes = self._fetch_quotes([m["symbol"] for m in members])
        return self._aggregate_block(members, quotes)

    def list_members_with_quotes(
        self,
        block_kind: str,
        block_name: str,
        *,
        limit: int = 300,
    ) -> list[dict[str, Any]]:
        """成分股列表并附带行情字段（单次批量拉取）??"""
        members = get_tdx_block_membership_cache().symbols_for_block(
            block_kind, block_name, limit=limit
        )
        if not members:
            return []
        quotes = self._fetch_quotes([m["symbol"] for m in members])
        rows: list[dict[str, Any]] = []
        for m in members:
            sym = m["symbol"]
            q = self._pick_quote(quotes, sym)
            rows.append(
                {
                    "symbol": sym,
                    "name": q.get("name") or m.get("name") or sym,
                    "price": q.get("price"),
                    "change_pct": q.get("change_pct"),
                    "change_amount": q.get("change_amount"),
                    "amount": q.get("amount"),
                    "volume": q.get("volume"),
                    "turnover": q.get("turnover"),
                    "volume_ratio": q.get("volume_ratio"),
                    "amplitude": q.get("amplitude"),
                    "pe": q.get("pe"),
                    "pb": q.get("pb"),
                    "industry": q.get("industry") or "",
                }
            )
        rows.sort(
            key=lambda r: float(r.get("change_pct") if r.get("change_pct") is not None else -1e9),
            reverse=True,
        )
        return rows

    def _aggregate_block(
        self,
        members: list[dict[str, str]],
        quotes: dict[str, dict[str, Any]],
    ) -> GenericResponseDTO:
        if not members:
            return {
                "change_pct": 0.0,
                "rise_ratio": None,
                "rise_count": 0,
                "fall_count": 0,
                "flat_count": 0,
                "leader_name": None,
                "leader_change_pct": None,
                "leader_symbol": None,
                "member_count": 0,
                "total_amount": 0.0,
                "avg_turnover": None,
            }

        enriched: list[dict[str, Any]] = []
        total_amount = 0.0
        turnovers: list[float] = []
        for m in members:
            q = self._pick_quote(quotes, m["symbol"])
            pct = float(q.get("change_pct") or 0)
            enriched.append({"name": q.get("name") or m.get("name") or "", "change_pct": pct})
            total_amount += float(q.get("amount") or 0)
            tr = q.get("turnover")
            if tr is not None:
                try:
                    turnovers.append(float(tr))
                except (TypeError, ValueError) as e:
                    logger.warning("tdx_block_stats_service.py._aggregate_block: %s", e)

        stats = aggregate_member_stats(enriched)
        stats["member_count"] = len(members)
        stats["total_amount"] = round(total_amount, 2)
        stats["avg_turnover"] = round(sum(turnovers) / len(turnovers), 4) if turnovers else None

        leader_sym = None
        best_pct: float | None = None
        for m in members:
            q = self._pick_quote(quotes, m["symbol"])
            try:
                pct = float(q.get("change_pct") if q.get("change_pct") is not None else -1e9)
            except (TypeError, ValueError):
                continue
            if best_pct is None or pct > best_pct:
                best_pct = pct
                leader_sym = m["symbol"]
        stats["leader_symbol"] = leader_sym
        return stats

    def _pick_quote(self, quotes: dict[str, dict[str, Any]], symbol: str) -> GenericResponseDTO:
        for key in self._symbol_keys(symbol):
            if key in quotes:
                return quotes[key]
        return {}

    def _load_blocks_meta(self, *, block_kind: str, limit: int) -> list[dict[str, Any]]:
        self._require_mysql()
        return require_tdx_block_read_port().list_blocks_meta(block_kind=block_kind, limit=limit)

    def _load_members_bulk(
        self,
        block_keys: list[tuple[str, str]],
        *,
        per_block_limit: int,
    ) -> GenericResponseDTO[tuple[str, str], list[dict[str, str]]]:
        if not block_keys:
            return {}
        self._require_mysql()
        return require_tdx_block_read_port().load_members_bulk(
            block_keys,
            per_block_limit=per_block_limit,
        )

    def _load_members(self, block_kind: str, block_name: str, *, limit: int) -> list[dict[str, str]]:
        key = self._block_key(block_kind, block_name)
        return self._load_members_bulk([key], per_block_limit=limit).get(key, [])

    def _fetch_quotes(self, symbols: list[str]) -> GenericResponseDTO[str, dict[str, Any]]:
        """仅走全市场快照（与市场全景同源）；快照未命中不再触发 Pytdx 联网??"""
        if not symbols:
            return {}
        snap = get_cn_quote_snapshot()
        snap.ensure_fresh()
        hits, missing = snap.lookup_map(symbols)
        if missing:
            logger.debug("tdx block quotes snapshot miss count=%s", len(missing))
            extra = self._quotes().fetch_map(missing, prefer_tdx=False)
            hits.update(extra)
        return hits
