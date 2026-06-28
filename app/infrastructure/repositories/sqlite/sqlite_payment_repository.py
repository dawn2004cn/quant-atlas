"""SQLite implementation of PaymentRepository."""

import json
import sqlite3
from pathlib import Path

from app.domain.payment_entities import GatewayConfig, PaymentIntent, PaymentStatus, Refund
from app.domain.ports import PaymentRepository


class SQLitePaymentRepository(PaymentRepository):
    """SQLite implementation of PaymentRepository."""

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else Path(".")
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        conn = sqlite3.connect(str(self._db_path), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS gateway_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    gateway_name TEXT NOT NULL,
                    api_key_hash TEXT,
                    config_json TEXT,
                    is_active INTEGER DEFAULT 1,
                    priority INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS payment_intents (
                    intent_id TEXT PRIMARY KEY,
                    amount REAL,
                    currency TEXT,
                    status TEXT,
                    gateway_id TEXT,
                    external_id TEXT,
                    customer_id TEXT,
                    metadata_json TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS payment_refunds (
                    refund_id TEXT PRIMARY KEY,
                    intent_id TEXT,
                    amount REAL,
                    status TEXT,
                    external_refund_id TEXT,
                    error_message TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            conn.commit()

    def save_payment_intent(self, intent: PaymentIntent) -> None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM payment_intents WHERE intent_id = ?",
                (intent.intent_id,)
            )
            existing = cur.fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO payment_intents (intent_id, amount, currency, status, gateway_id, external_id, customer_id, metadata_json, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent.intent_id,
                        intent.amount,
                        intent.currency,
                        intent.status.value,
                        intent.gateway_id,
                        intent.external_id,
                        intent.customer_id,
                        json.dumps(intent.metadata) if intent.metadata else "{}",
                        intent.error_message
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE payment_intents SET
                        amount = ?,
                        currency = ?,
                        status = ?,
                        gateway_id = ?,
                        external_id = ?,
                        customer_id = ?,
                        metadata_json = ?,
                        error_message = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE intent_id = ?
                    """,
                    (
                        intent.amount,
                        intent.currency,
                        intent.status.value,
                        intent.gateway_id,
                        intent.external_id,
                        intent.customer_id,
                        json.dumps(intent.metadata) if intent.metadata else "{}",
                        intent.error_message,
                        intent.intent_id
                    )
                )
            conn.commit()

    def get_payment_intent(self, intent_id: str) -> PaymentIntent | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM payment_intents WHERE intent_id = ?",
                (intent_id,)
            )
            row = cur.fetchone()
            if not row:
                return None
            return self._map_row_to_intent(row)

    def list_gateways(self, only_active: bool = True) -> list[GatewayConfig]:
        with self._connect() as conn:
            if only_active:
                cur = conn.execute(
                    "SELECT * FROM gateway_configs WHERE is_active = 1 ORDER BY priority DESC"
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM gateway_configs ORDER BY priority DESC"
                )
            rows = cur.fetchall()
            return [self._map_row_to_gateway(r) for r in rows]

    def save_refund(self, refund: Refund) -> None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM payment_refunds WHERE refund_id = ?",
                (refund.refund_id,)
            )
            existing = cur.fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO payment_refunds (refund_id, intent_id, amount, status, external_refund_id, error_message)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        refund.refund_id,
                        refund.intent_id,
                        refund.amount,
                        refund.status.value,
                        refund.external_refund_id,
                        refund.error_message
                    )
                )
            else:
                conn.execute(
                    """
                    UPDATE payment_refunds SET
                        intent_id = ?,
                        amount = ?,
                        status = ?,
                        external_refund_id = ?,
                        error_message = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE refund_id = ?
                    """,
                    (
                        refund.intent_id,
                        refund.amount,
                        refund.status.value,
                        refund.external_refund_id,
                        refund.error_message,
                        refund.refund_id
                    )
                )
            conn.commit()

    def _map_row_to_intent(self, row) -> PaymentIntent:
        return PaymentIntent(
            intent_id=row["intent_id"],
            amount=row["amount"],
            currency=row["currency"],
            status=PaymentStatus(row["status"]),
            gateway_id=row["gateway_id"],
            external_id=row["external_id"],
            customer_id=row["customer_id"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def _map_row_to_gateway(self, row) -> GatewayConfig:
        return GatewayConfig(
            id=row["id"],
            gateway_name=row["gateway_name"],
            api_key_hash=row["api_key_hash"],
            config_json=row["config_json"] or "{}",
            is_active=bool(row["is_active"]),
            priority=row["priority"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
