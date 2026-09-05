from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""A 股全市场行情快照（与市场全景 /markets/CN/quotes 同源，内存索引供板块等复用）。"""


import threading
import time
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)

_DEFAULT_TTL_SEC = 45
# Page-path hydrate: liquid seeds via Tencent only. Never pull the full A-share book.
_PAGE_SEED_MAX = 80


def _symbol_index_keys(symbol: str) -> list[str]:
    raw = str(symbol or "").strip()
    if not raw:
        return []
    norm = raw.split(":", 1)[1] if ":" in raw else raw
    keys = {raw, norm, norm.lower()}
    if norm.lower().startswith(("sh", "sz", "bj")):
        keys.add(norm[2:])
    digits = "".join(ch for ch in norm if ch.isdigit())[-6:].zfill(6)
    if digits and digits != "000000":
        keys.add(digits)
    return list(keys)


def _row_to_payload(row: dict[str, Any]) -> GenericResponseDTO:
    code = str(row.get("code") or row.get("symbol") or "")
    code6 = "".join(ch for ch in code if ch.isdigit())[-6:].zfill(6) or code
    return {
        "code": code6,
        "name": str(row.get("name") or ""),
        "price": float(row.get("price", 0) or 0),
        "change_amount": float(row.get("change_amount", row.get("change", 0)) or 0),
        "change_pct": float(row.get("change_pct", row.get("pct_chg", 0)) or 0),
        "volume": float(row.get("volume", 0) or 0),
        "amount": float(row.get("amount", 0) or 0),
        "turnover": float(row.get("turnover", 0) or 0),
        "volume_ratio": float(row.get("volume_ratio", 0) or 0),
        "amplitude": float(row.get("amplitude", 0) or 0),
        "pe": float(row.get("pe", 0) or 0),
        "pb": float(row.get("pb", 0) or 0),
        "industry": str(row.get("industry") or ""),
        "source": str(row.get("source") or "snapshot"),
    }


def _board_of(code: str) -> str:
    c = str(code or "")
    if c.startswith("688") or c.startswith("689"):
        return "kc"
    if c.startswith("300") or c.startswith("301"):
        return "cyb"
    if c.startswith("4") or c.startswith("8") or c.startswith("92"):
        return "bj"
    if c.startswith(("600", "601", "603", "605")):
        return "sh"
    if c.startswith(("000", "001", "002", "003")):
        return "sz"
    return ""


def _market_breadth_stats(rows: list[dict[str, Any]]) -> dict[str, int]:
    up = down = flat = limit_up = limit_down = 0
    for row in rows:
        chg = float(row.get("change_pct") or 0)
        if chg >= 9.9:
            limit_up += 1
        if chg <= -9.9:
            limit_down += 1
        if chg > 0:
            up += 1
        elif chg < 0:
            down += 1
        else:
            flat += 1
    return {
        "total": len(rows),
        "up": up,
        "down": down,
        "flat": flat,
        "limit_up": limit_up,
        "limit_down": limit_down,
    }


def _code6(code: str) -> str:
    return "".join(ch for ch in str(code or "") if ch.isdigit())[-6:].zfill(6)


class CnQuoteSnapshot:
    """进程内 quote 索引。页面路径只读 cache，空则腾讯种子补活，绝不走 AkShare。"""

    def __init__(
        self,
        *,
        market_service: object | None = None,
        market_provider: object | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SEC,
    ) -> None:
        self._market_service = market_service
        self._market_provider = market_provider
        self._ttl = max(1, int(ttl_seconds))
        self._lock = threading.RLock()
        self._by_key: dict[str, dict[str, Any]] = {}
        self._updated_at: float = 0.0
        self._row_count = 0

    @property
    def row_count(self) -> int:
        return self._row_count

    @property
    def age_seconds(self) -> float:
        if not self._updated_at:
            return 1e9
        return time.time() - self._updated_at

    def is_warm(self) -> bool:
        return bool(self._by_key) and self.age_seconds < self._ttl

    @property
    def is_refreshing(self) -> bool:
        return False

    def load_rows(self, rows: list[dict[str, Any]]) -> None:
        """由 /markets/CN/quotes 等接口写入，避免重复读库。"""
        with self._lock:
            self._rebuild(rows)
            self._updated_at = time.time()

    def ensure_fresh(self, *, force: bool = False) -> None:
        """Load local cache only. If empty, hydrate a bounded Tencent seed list.

        Never calls ``list_quotes(CN, None)`` / AkShare. Full-market books stay
        off the page path so a hung or OOM-prone AkShare pull cannot crash Flask.
        """
        if not force and self.is_warm():
            return
        with self._lock:
            if not force and self.is_warm():
                return
            rows = self._load_cached_only()
            if rows:
                self._rebuild(rows)
                self._updated_at = time.time()
                logger.info("CnQuoteSnapshot cache load: %s symbols", self._row_count)
                return
        self._hydrate_tencent_seed()

    def _hydrate_tencent_seed(self) -> None:
        """Fill an empty snapshot from Tencent + seed codes. No AkShare."""
        svc = self._market_service
        if svc is None or not hasattr(svc, "list_quotes_tencent"):
            return
        try:
            rows = svc.list_quotes_tencent(max_symbols=_PAGE_SEED_MAX)
        except TypeError:
            try:
                rows = svc.list_quotes_tencent()
            except Exception as exc:
                logger.warning("CnQuoteSnapshot tencent seed failed: %s", exc)
                return
        except Exception as exc:
            logger.warning("CnQuoteSnapshot tencent seed failed: %s", exc)
            return
        if rows:
            self.load_rows(rows)
            logger.info("CnQuoteSnapshot tencent seed: %s symbols", self._row_count)

    def fill_missing(self, symbols: list[str], *, fetcher) -> None:
        """Live-fetch snapshot misses so symbol lists (sectors / radar) are not empty."""
        if not symbols:
            return
        _hits, missing = self.lookup_rows(symbols)
        if not missing:
            return
        try:
            extra = fetcher(missing) or []
        except Exception as exc:
            logger.warning("CnQuoteSnapshot fill_missing failed: %s", exc)
            return
        if not extra:
            return
        with self._lock:
            self._rebuild(self.unique_rows() + list(extra))

    def lookup_map(self, symbols: list[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """返回 (命中索引, 未命中 normalized 列表)。"""
        hits, missing = self.lookup_rows(symbols)
        out: dict[str, dict[str, Any]] = {}
        for payload in hits:
            code = str(payload.get("code") or "")
            for key in _symbol_index_keys(code):
                out[key] = payload
        for sym in symbols:
            payload = self._pick_one(sym)
            if not payload:
                continue
            for key in _symbol_index_keys(sym):
                out[key] = payload
        return out, missing

    def lookup_rows(self, symbols: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        """按输入顺序返回去重行情行与未命中代码（先 ensure_fresh）。"""
        self.ensure_fresh()
        hits: list[dict[str, Any]] = []
        missing: list[str] = []
        seen_codes: set[str] = set()
        seen_missing: set[str] = set()
        for sym in symbols:
            payload = self._pick_one(sym)
            if payload:
                code = str(payload.get("code") or "")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    hits.append(payload)
                continue
            try:
                from app.domain.shared.symbol_normalizer import SymbolNormalizer

                n = SymbolNormalizer().normalize(sym)
            except Exception:
                n = str(sym).strip()
            if n and n not in seen_missing:
                seen_missing.add(n)
                missing.append(n)
        return hits, missing

    def _pick_one(self, symbol: str) -> GenericResponseDTO | None:
        for key in _symbol_index_keys(symbol):
            if key in self._by_key:
                return self._by_key[key]
        return None

    def _rebuild(self, rows: list[dict[str, Any]]) -> None:
        by_key: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not row:
                continue
            if hasattr(row, "__dict__") and not isinstance(row, dict):
                from dataclasses import asdict, is_dataclass

                if is_dataclass(row):
                    row = asdict(row)
                else:
                    row = vars(row)
            payload = _row_to_payload(row)
            if not payload.get("code"):
                continue
            for key in _symbol_index_keys(payload["code"]):
                by_key[key] = payload
        self._by_key = by_key
        self._row_count = len({p.get("code") for p in by_key.values() if p.get("code")})

    def unique_rows(self) -> list[dict[str, Any]]:
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        for payload in self._by_key.values():
            code = str(payload.get("code") or "")
            if not code or code in seen:
                continue
            seen.add(code)
            rows.append(payload)
        return rows

    def query_page(
        self,
        *,
        page: int = 1,
        page_size: int = 40,
        sort_key: str = "change_pct",
        sort_order: str = "desc",
        board_filter: str = "all",
        codes: set[str] | None = None,
    ) -> dict[str, Any]:
        """Filter, sort and paginate in-process snapshot (one full load per TTL)."""
        rows = self.unique_rows()
        if codes:
            allow = {_code6(c) for c in codes if c}
            rows = [r for r in rows if _code6(str(r.get("code") or "")) in allow]
        filt = str(board_filter or "all").lower()
        if filt == "limit_up":
            rows = [r for r in rows if float(r.get("change_pct") or 0) >= 9.9]
        elif filt == "limit_down":
            rows = [r for r in rows if float(r.get("change_pct") or 0) <= -9.9]
        elif filt == "up":
            rows = [r for r in rows if float(r.get("change_pct") or 0) > 0]
        elif filt == "down":
            rows = [r for r in rows if float(r.get("change_pct") or 0) < 0]
        elif filt in {"sh", "sz", "bj", "cyb", "kc"}:
            rows = [r for r in rows if _board_of(str(r.get("code") or "")) == filt]

        key = sort_key if sort_key in {
            "change_pct", "price", "amount", "turnover", "pe", "total_market_cap", "code", "name",
        } else "change_pct"
        reverse = str(sort_order or "desc").lower() != "asc"

        def _sort_val(row: dict[str, Any]) -> float | str:
            val = row.get(key)
            if key in {"code", "name"}:
                return str(val or "")
            try:
                return float(val or 0)
            except (TypeError, ValueError):
                return 0.0

        rows.sort(key=_sort_val, reverse=reverse)
        total = len(rows)
        page = max(1, int(page))
        page_size = max(1, min(200, int(page_size)))
        start = (page - 1) * page_size
        items = rows[start : start + page_size]
        with self._lock:
            stale = bool(self._by_key) and self.age_seconds >= self._ttl
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "stats": _market_breadth_stats(self.unique_rows()),
            "warming": False,
            "stale": stale,
        }

    def _load_cached_only(self) -> list[dict[str, Any]]:
        if self._market_service is not None:
            try:
                list_quotes = self._market_service.list_quotes
                try:
                    rows = list_quotes(MarketCode.CN, None, live=False)
                except TypeError:
                    rows = []
                if rows:
                    return rows
            except Exception as exc:
                logger.warning("CnQuoteSnapshot cache list_quotes failed: %s", exc)

        if self._market_provider is not None and hasattr(
            self._market_provider, "get_realtime_quotes"
        ):
            try:
                from app.domain.dto.quote_factory import quote_to_dict

                quotes = self._market_provider.get_realtime_quotes(market=MarketCode.CN) or []
                return [quote_to_dict(q) for q in quotes]
            except Exception as exc:
                logger.warning("CnQuoteSnapshot provider cache scan failed: %s", exc)
        return []


_snapshot: CnQuoteSnapshot | None = None
_snapshot_lock = threading.Lock()


def configure_cn_quote_snapshot(
    *,
    market_service: object | None = None,
    market_provider: object | None = None,
    ttl_seconds: int = _DEFAULT_TTL_SEC,
) -> CnQuoteSnapshot:
    global _snapshot
    with _snapshot_lock:
        _snapshot = CnQuoteSnapshot(
            market_service=market_service,
            market_provider=market_provider,
            ttl_seconds=ttl_seconds,
        )
        return _snapshot


def get_cn_quote_snapshot() -> CnQuoteSnapshot:
    global _snapshot
    if _snapshot is None:
        with _snapshot_lock:
            if _snapshot is None:
                from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

                _snapshot = CnQuoteSnapshot(market_provider=get_market_data_provider())
    return _snapshot
