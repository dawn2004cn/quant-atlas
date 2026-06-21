"""Biometric Strategy Vault — Phase 18.3.
Strategy integrity fingerprint + truth watermark generator."""

from __future__ import annotations

import hashlib
import hmac
import json
import struct
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyFingerprint:
    """Biometric-style integrity fingerprint for a strategy."""
    strategy_id: str
    user_id: int
    fingerprint_hash: str
    algorithm: str = "sha256"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verified_at: str = ""


@dataclass
class TruthWatermark:
    """Cryptographic watermark for data authenticity verification."""
    symbol: str
    market: str
    timestamp: str
    data_hash: str
    watermark_b64: str
    source_signature: str = "guardian_v1"


class StrategyVaultService:
    """Strategy integrity protection with biometric-style fingerprints."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "strategy_fingerprints.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._secret_key = self._load_or_create_key(root)

    def _load_or_create_key(self, root: Path) -> bytes:
        """Load or create a persistent HMAC key."""
        key_path = root / "instance" / ".strategy_vault_key"
        if key_path.exists():
            return key_path.read_bytes()
        key = hashlib.sha256(str(time.time()).encode()).digest()
        key_path.write_bytes(key)
        return key

    def fingerprint_strategy(self, strategy_id: str, user_id: int, strategy_logic: str) -> StrategyFingerprint:
        """Generate a biometric-style integrity fingerprint for a strategy."""
        raw = f"{strategy_id}:{user_id}:{strategy_logic}:{datetime.now(timezone.utc).isoformat()}"
        h = hmac.new(self._secret_key, raw.encode(), hashlib.sha256)
        fingerprint = StrategyFingerprint(
            strategy_id=strategy_id,
            user_id=user_id,
            fingerprint_hash=h.hexdigest(),
        )
        self._persist(fingerprint)
        return fingerprint

    def verify_fingerprint(self, strategy_id: str, user_id: int, strategy_logic: str) -> bool:
        """Verify strategy integrity by recomputing fingerprint."""
        raw = f"{strategy_id}:{user_id}:{strategy_logic}:"
        # Find the creation timestamp from stored fingerprint
        stored = self._get_fingerprint(strategy_id, user_id)
        if not stored:
            return False
        raw += stored.created_at
        expected = hmac.new(self._secret_key, raw.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, stored.fingerprint_hash)

    def _persist(self, fp: StrategyFingerprint) -> None:
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "strategy_id": fp.strategy_id,
                "user_id": fp.user_id,
                "fingerprint_hash": fp.fingerprint_hash,
                "algorithm": fp.algorithm,
                "created_at": fp.created_at,
            }) + "\n")

    def _get_fingerprint(self, strategy_id: str, user_id: int) -> StrategyFingerprint | None:
        if not self._store.exists():
            return None
        with self._store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("strategy_id") == strategy_id and int(data.get("user_id", -1)) == user_id:
                    return StrategyFingerprint(**data)
        return None


class TruthWatermarkService:
    """Generates cryptographic data watermarks for UI chart authenticity."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "truth_watermarks.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def generate_watermark(self, symbol: str, market: str, data_payload: dict) -> TruthWatermark:
        """Generate a verifiable watermark for a data point."""
        ts = datetime.now(timezone.utc).isoformat()
        payload_str = json.dumps(data_payload, sort_keys=True)
        data_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]

        # Create a compact watermark string
        watermark_raw = f"QA|{symbol}|{market}|{ts}|{data_hash}"
        watermark_b64 = watermark_raw.encode("utf-8").hex()

        wm = TruthWatermark(
            symbol=symbol,
            market=market,
            timestamp=ts,
            data_hash=data_hash,
            watermark_b64=watermark_b64,
        )
        self._persist(wm)
        return wm

    def verify_watermark(self, watermark_b64: str, data_payload: dict) -> dict:
        """Verify a watermark against current data."""
        try:
            decoded = bytes.fromhex(watermark_b64).decode("utf-8")
            parts = decoded.split("|")
            if len(parts) < 5 or parts[0] != "QA":
                return {"ok": False, "error": "invalid_format"}

            symbol, market, ts, expected_hash = parts[1], parts[2], parts[3], parts[4]
            payload_str = json.dumps(data_payload, sort_keys=True)
            actual_hash = hashlib.sha256(payload_str.encode()).hexdigest()[:16]

            is_valid = actual_hash == expected_hash
            return {
                "ok": is_valid,
                "symbol": symbol,
                "market": market,
                "timestamp": ts,
                "data_hash": expected_hash,
                "message": "数据真实有效" if is_valid else "数据已被篡改或已过期",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _persist(self, wm: TruthWatermark) -> None:
        try:
            with self._store.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "symbol": wm.symbol,
                    "market": wm.market,
                    "timestamp": wm.timestamp,
                    "data_hash": wm.data_hash,
                    "watermark_b64": wm.watermark_b64,
                }) + "\n")
        except Exception as exc:
            logger.warning("Watermark persist failed: %s", exc)
