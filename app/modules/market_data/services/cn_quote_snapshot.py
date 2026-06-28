from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""A 股全市场行情快照（与市场全景 /markets/CN/quotes 同源，内存索引供板块等复用）。"""


import threadingimport timefrom typing import Anyfrom app.core.logger import get_loggerfrom app.domain.enums import MarketCodelogger = get_logger(__name__)

_DEFAULT_TTL_SEC = 45


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


class CnQuoteSnapshot:
    """进程内全市场 quote 索引；与 market-panorama 使用同一 stock_cache / list_quotes 数据源。"""

    def __init__(
        self,
        *,
        market_service: object | None = None,
        market_provider: object | None = None,
        ttl_seconds: int = _DEFAULT_TTL_SEC,
    ) -> None:
        self._market_service = market_service
        self._market_provider = market_provider
        self._ttl = max(15, int(ttl_seconds))
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

    def load_rows(self, rows: list[dict[str, Any]]) -> None:
        """由 /markets/CN/quotes 等接口写入，避免重复读库。"""
        with self._lock:
            self._rebuild(rows)
            self._updated_at = time.time()

    def ensure_fresh(self, *, force: bool = False) -> None:
        if not force and self.is_warm():
            return
        with self._lock:
            if not force and self.is_warm():
                return
            rows = self._load_from_services()
            self._rebuild(rows)
            self._updated_at = time.time()
            logger.info("CnQuoteSnapshot refreshed: %s symbols", self._row_count)

    def lookup_map(self, symbols: list[str]) -> tuple[dict[str, dict[str, Any]], list[str]]:
        """返回 (命中索引, 未命中 normalized 列表)。"""
        self.ensure_fresh()
        out: dict[str, dict[str, Any]] = {}
        missing: list[str] = []
        seen_missing: set[str] = set()
        for sym in symbols:
            payload = self._pick_one(sym)
            if payload:
                for key in _symbol_index_keys(sym):
                    out[key] = payload
            else:
                try:
                    from app.domain.shared.symbol_normalizer import SymbolNormalizer

                    n = SymbolNormalizer().normalize(sym)
                except Exception:
                    n = str(sym).strip()
                if n and n not in seen_missing:
                    seen_missing.add(n)
                    missing.append(n)
        return out, missing

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

    def _load_from_services(self) -> list[dict[str, Any]]:
        if self._market_service is not None:
            try:
                rows = self._market_service.list_quotes(MarketCode.CN, None)
                if rows:
                    return rows
            except Exception as exc:
                logger.warning("CnQuoteSnapshot list_quotes failed: %s", exc)

        if self._market_provider is not None and hasattr(
            self._market_provider, "get_realtime_quotes"
        ):
            try:
                from app.domain.dto.quote_factory import quote_to_dict

                quotes = self._market_provider.get_realtime_quotes(market=MarketCode.CN) or []
                return [quote_to_dict(q) for q in quotes]
            except Exception as exc:
                logger.warning("CnQuoteSnapshot provider scan failed: %s", exc)
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
