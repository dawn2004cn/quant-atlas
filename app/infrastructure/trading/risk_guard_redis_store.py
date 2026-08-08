"""Redis persistence for Risk Guard account snapshots (DIF B4 / REQ-SRS-01)."""

from __future__ import annotations

import json
from typing import Any, Protocol

from app.core.logger import get_logger
from app.modules.execution.services.risk_guard_service import AccountRiskSnapshot

logger = get_logger(__name__)

_DEFAULT_EQUITY = 100_000.0


class _RedisLike(Protocol):
    def get(self, key: str) -> Any: ...

    def set(self, key: str, value: str, ex: int | None = None) -> Any: ...


class RedisRiskGuardStore:
    """Persist day equity / stop-out / suspend flag across process restarts."""

    def __init__(
        self,
        *,
        client: _RedisLike | None = None,
        redis_url: str | None = None,
        key_prefix: str = "qa:risk_guard:",
        ttl_seconds: int = 60 * 60 * 36,
    ) -> None:
        self._key_prefix = key_prefix
        self._ttl = int(ttl_seconds)
        self._client = client
        self._redis_url = (redis_url or "").strip() or None

    def _redis(self) -> _RedisLike:
        if self._client is not None:
            return self._client
        from app.infrastructure.redis_client import RedisClientPool

        if not self._redis_url:
            raise RuntimeError("redis_url_required_for_risk_guard_store")
        self._client = RedisClientPool.get(self._redis_url).client
        return self._client

    def _key(self, account_id: str) -> str:
        return f"{self._key_prefix}{account_id}"

    def get_snapshot(self, account_id: str) -> AccountRiskSnapshot:
        try:
            raw = self._redis().get(self._key(account_id))
        except Exception:
            logger.warning("risk_guard redis get failed account=%s", account_id, exc_info=True)
            return AccountRiskSnapshot(equity=_DEFAULT_EQUITY, day_start_equity=_DEFAULT_EQUITY)
        if not raw:
            return AccountRiskSnapshot(equity=_DEFAULT_EQUITY, day_start_equity=_DEFAULT_EQUITY)
        try:
            data = json.loads(raw) if isinstance(raw, (str, bytes, bytearray)) else dict(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("risk_guard redis corrupt snapshot account=%s", account_id, exc_info=True)
            return AccountRiskSnapshot(equity=_DEFAULT_EQUITY, day_start_equity=_DEFAULT_EQUITY)
        return AccountRiskSnapshot(
            equity=float(data.get("equity", _DEFAULT_EQUITY)),
            day_start_equity=float(data.get("day_start_equity", _DEFAULT_EQUITY)),
            consecutive_stop_outs=int(data.get("consecutive_stop_outs") or 0),
            execution_suspended=bool(data.get("execution_suspended")),
        )

    def set_snapshot(self, account_id: str, snapshot: AccountRiskSnapshot) -> None:
        payload = {
            "equity": snapshot.equity,
            "day_start_equity": snapshot.day_start_equity,
            "consecutive_stop_outs": snapshot.consecutive_stop_outs,
            "execution_suspended": snapshot.execution_suspended,
        }
        try:
            self._redis().set(
                self._key(account_id),
                json.dumps(payload, ensure_ascii=False),
                ex=self._ttl,
            )
        except Exception:
            logger.warning("risk_guard redis set failed account=%s", account_id, exc_info=True)
