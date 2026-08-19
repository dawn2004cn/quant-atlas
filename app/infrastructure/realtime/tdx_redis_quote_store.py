"""Redis-backed TDX realtime quote cache for CN A-shares."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.core.runtime_config import get_runtime, get_runtime_int, resolved_redis_url
from app.domain.dto.quote_factory import canonical_quote_payload
from app.domain.enums import MarketCode
from app.domain.shared.value_objects import StockQuote

logger = logging.getLogger(__name__)

_KEY_PREFIX = "qa:tdx:quote:cn:"
_META_KEY = "qa:tdx:quote:cn:_meta"
_PUB_CHANNEL = "qa:tdx:quote:cn:pub"


def _default_ttl_sec() -> int:
    return max(30, min(get_runtime_int("TDX_REDIS_QUOTE_TTL_SEC", 120), 600))


def _normalize_code(code: str) -> str:
    digits = "".join(ch for ch in str(code or "") if ch.isdigit())
    return digits[-6:].zfill(6) if digits else str(code or "").strip().upper()


class TdxRedisQuoteStore:
    """Write/read TDX quotes in Redis; optional pub/sub for WS fan-out."""

    def __init__(self, redis_url: str | None = None) -> None:
        self._url = (redis_url or resolved_redis_url("")).strip()
        self._client: Any | None = None
        self._ttl = _default_ttl_sec()

    @property
    def available(self) -> bool:
        if not self._url:
            return False
        try:
            return bool(self._redis().ping())
        except Exception:
            return False

    def _redis(self) -> Any:
        if self._client is None:
            from app.infrastructure.redis_client import RedisClientPool

            RedisClientPool.set_default_url(self._url)
            self._client = RedisClientPool.get(self._url).client
        return self._client

    def _key(self, code: str) -> str:
        return f"{_KEY_PREFIX}{_normalize_code(code)}"

    def write_batch(self, quotes: list[dict[str, Any]], *, source: str = "tdx") -> int:
        if not quotes or not self.available:
            return 0
        pipe = self._redis().pipeline(transaction=False)
        now_ms = int(time.time() * 1000)
        n = 0
        for raw in quotes:
            payload = canonical_quote_payload(dict(raw), market=MarketCode.CN.value)
            code = _normalize_code(str(payload.get("code") or payload.get("symbol") or ""))
            if not code:
                continue
            payload["source"] = source
            payload["updated_at_ms"] = now_ms
            blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            pipe.setex(self._key(code), self._ttl, blob)
            n += 1
        meta = json.dumps(
            {"updated_at_ms": now_ms, "count": n, "source": source},
            ensure_ascii=False,
        )
        pipe.setex(_META_KEY, self._ttl, meta)
        try:
            pipe.execute()
            try:
                self._redis().publish(_PUB_CHANNEL, meta)
            except Exception as exc:  # noqa: BLE001
                logger.debug("tdx quote pub skipped: %s", exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("tdx redis write_batch failed: %s", exc, exc_info=True)
            return 0
        return n

    def get_quote_dict(self, code: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        try:
            blob = self._redis().get(self._key(code))
            if not blob:
                return None
            return json.loads(blob)
        except Exception as exc:  # noqa: BLE001
            logger.debug("tdx redis get %s: %s", code, exc)
            return None

    def get_quotes_dict(self, codes: list[str]) -> dict[str, dict[str, Any]]:
        if not codes or not self.available:
            return {}
        keys = [self._key(c) for c in codes]
        try:
            blobs = self._redis().mget(keys)
        except Exception as exc:  # noqa: BLE001
            logger.debug("tdx redis mget: %s", exc)
            return {}
        out: dict[str, dict[str, Any]] = {}
        for code, blob in zip(codes, blobs or [], strict=False):
            if not blob:
                continue
            try:
                payload = json.loads(blob)
                nc = _normalize_code(str(payload.get("code") or code))
                out[nc] = payload
            except json.JSONDecodeError:
                continue
        return out

    def get_meta(self) -> dict[str, Any]:
        if not self.available:
            return {}
        try:
            blob = self._redis().get(_META_KEY)
            return json.loads(blob) if blob else {}
        except Exception:
            return {}

    def is_fresh(self, max_age_sec: float | None = None) -> bool:
        meta = self.get_meta()
        if not meta.get("updated_at_ms"):
            return False
        age_limit = float(max_age_sec if max_age_sec is not None else get_runtime_int("TDX_REDIS_MAX_AGE_SEC", 15))
        age_ms = int(time.time() * 1000) - int(meta["updated_at_ms"])
        return age_ms <= age_limit * 1000

    def to_stock_quotes(self, payloads: dict[str, dict[str, Any]]) -> list[StockQuote]:
        from datetime import datetime

        out: list[StockQuote] = []
        for code, p in payloads.items():
            price = float(p.get("price") or 0)
            if price <= 0:
                continue
            out.append(
                StockQuote(
                    code=_normalize_code(code),
                    name=str(p.get("name") or code),
                    market=MarketCode.CN,
                    price=price,
                    change_pct=float(p.get("change_pct") or 0),
                    volume=float(p.get("volume") or 0),
                    amount=float(p.get("amount") or 0),
                    turnover=float(p.get("turnover") or 0),
                    open_price=float(p.get("open_price") or p.get("open") or 0),
                    high_price=float(p.get("high_price") or p.get("high") or 0),
                    low_price=float(p.get("low_price") or p.get("low") or 0),
                    source=str(p.get("source") or "tdx_redis"),
                    updated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    change_amount=float(p.get("change_amount") or 0),
                    prev_close=float(p.get("prev_close") or 0),
                    volume_ratio=float(p.get("volume_ratio") or 0),
                    amplitude=float(p.get("amplitude") or 0),
                    pe=float(p.get("pe") or 0),
                    pb=float(p.get("pb") or 0),
                    total_market_cap=float(p.get("total_market_cap") or 0),
                    industry=str(p.get("industry") or ""),
                )
            )
        return out


def tdx_redis_feed_enabled() -> bool:
    from app.core.runtime_config import get_runtime_bool

    return get_runtime_bool("TDX_REDIS_FEED", True)


def tdx_redis_read_enabled() -> bool:
    from app.core.runtime_config import get_runtime_bool

    if not get_runtime_bool("TDX_REDIS_READ", True):
        return False
    if not tdx_redis_feed_enabled():
        return get_runtime_bool("TDX_REDIS_READ_WITHOUT_FEED", False)
    return True


__all__ = [
    "TdxRedisQuoteStore",
    "tdx_redis_feed_enabled",
    "tdx_redis_read_enabled",
]
