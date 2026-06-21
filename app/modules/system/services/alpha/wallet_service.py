from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class WalletEntry:
    user_id: int
    balance: float
    updated_at: str


class WalletService:
    def __init__(self, store_path: str | Path | None = None, broker: Any = None):
        root = Path(__file__).resolve().parents[4]
        self._store_path = Path(store_path) if store_path else root / "instance" / "wallet_balances.jsonl"
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[int, WalletEntry] = {}
        self._broker = broker
        if self._broker is not None:
            from app.core.data_write_broker import WriteBackend
            self._broker.register_writer(WriteBackend.JSONL, "wallet", self._persist_via_broker)

    def _persist_via_broker(self, data: dict) -> bool:
        return self._raw_persist(WalletEntry(**data))

    def get_balance(self, user_id: int) -> float:
        entry = self._get_entry(user_id)
        return entry.balance if entry else 0.0

    def credit(self, user_id: int, amount: float, reason: str = "") -> float:
        if amount <= 0:
            raise ValueError(f"Credit amount must be positive: {amount}")
        entry = self._get_entry(user_id) or WalletEntry(
            user_id=user_id, balance=0.0, updated_at=""
        )
        entry.balance += amount
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist(entry)
        logger.info("Wallet credit user=%s amount=%s reason=%s balance=%s", user_id, amount, reason, entry.balance)
        return entry.balance

    def debit(self, user_id: int, amount: float, reason: str = "") -> float:
        if amount <= 0:
            raise ValueError(f"Debit amount must be positive: {amount}")
        entry = self._get_entry(user_id)
        if not entry or entry.balance < amount:
            raise ValueError(f"Insufficient balance for user {user_id}: need {amount}, have {entry.balance if entry else 0}")
        entry.balance -= amount
        entry.updated_at = datetime.now(timezone.utc).isoformat()
        self._persist(entry)
        logger.info("Wallet debit user=%s amount=%s reason=%s balance=%s", user_id, amount, reason, entry.balance)
        return entry.balance

    def transfer(self, from_user: int, to_user: int, amount: float, reason: str = "") -> None:
        self.debit(from_user, amount, reason)
        self.credit(to_user, amount, reason)

    def _get_entry(self, user_id: int) -> WalletEntry | None:
        if user_id in self._cache:
            return self._cache[user_id]
        if not self._store_path.exists():
            return None
        with self._store_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("user_id", -1)) == user_id:
                    entry = WalletEntry(**data)
                    self._cache[user_id] = entry
                    return entry
        return None

    def _persist(self, entry: WalletEntry) -> None:
        self._raw_persist(entry)
        self._cache[entry.user_id] = entry

    def _raw_persist(self, entry: WalletEntry) -> bool:
        with self._store_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
        return True


__all__ = ["WalletService", "WalletEntry"]