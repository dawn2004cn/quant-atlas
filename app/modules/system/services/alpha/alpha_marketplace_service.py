from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.modules.system.services.alpha.tokenized_alpha_service import TokenizedAlphaService

logger = get_logger(__name__)


@dataclass
class Listing:
    listing_id: str
    token_id: str
    seller_id: int
    reputation_cost: float
    signal_count: int = 100
    active: bool = True
    diversity_bonus: float = 0.0
    zk_proof_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def price_tokens(self) -> float:
        """Backward-compatible alias for legacy clients."""
        return self.reputation_cost


@dataclass
class Order:
    order_id: str
    listing_id: str
    buyer_id: int
    reputation_spent: float
    signal_count: int
    status: str = "active"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def tokens_spent(self) -> float:
        """Backward-compatible alias for legacy clients."""
        return self.reputation_spent


@dataclass
class SignalDelivery:
    delivery_id: str
    order_id: str
    symbol: str
    signal_value: float
    timestamp: str
    delivered: bool = False


class AlphaMarketplaceService:
    """Compliance-pivot marketplace: contribute/reward via reputation, not currency."""

    _SELLER_REWARD_RATIO = 0.5
    _DIVERSITY_BONUS_MULTIPLIER = 0.2

    def __init__(
        self,
        token_service: TokenizedAlphaService | None = None,
        compliance_service: Any | None = None,
        evolution_service: Any | None = None,
        wallet_service: Any | None = None,
        broker: Any | None = None,
    ):
        self._token_svc = token_service or TokenizedAlphaService()
        self._compliance = compliance_service
        self._evolution = evolution_service
        self._wallet = wallet_service  # deprecated; kept for legacy wallet endpoints
        root = Path(__file__).resolve().parents[4]
        self._listing_store = root / "instance" / "alpha_listings.jsonl"
        self._order_store = root / "instance" / "alpha_orders.jsonl"
        self._signal_store_root = root / "instance" / "alpha_signal_deliveries"
        self._listing_store.parent.mkdir(parents=True, exist_ok=True)
        self._signal_store_root.mkdir(parents=True, exist_ok=True)

    def _get_compliance(self) -> Any:
        if self._compliance is None:
            from app.modules.system.services.compliance_service import ComplianceService

            self._compliance = ComplianceService()
        return self._compliance

    def _get_evolution(self) -> Any:
        if self._evolution is None:
            from app.modules.system.services.anti_decay_evolution_service import AntiDecayEvolutionService

            self._evolution = AntiDecayEvolutionService()
        return self._evolution

    @property
    def wallet(self) -> Any:
        """Deprecated wallet accessor — use compliance reputation instead."""
        if self._wallet is None:
            from app.modules.system.services.alpha.wallet_service import WalletService

            self._wallet = WalletService()
        return self._wallet

    def list_token(
        self,
        token_id: str,
        seller_id: int,
        price_tokens: float,
        signal_count: int = 100,
        *,
        reputation_cost: float | None = None,
    ) -> Listing:
        manifest = self._token_svc.get_manifest(token_id)
        if not manifest:
            raise ValueError(f"Token {token_id} not found")
        if manifest.visibility != "public":
            raise ValueError("Only public tokens can be listed")

        cost = reputation_cost if reputation_cost is not None else price_tokens
        diversity_bonus = self._compute_listing_diversity(token_id)

        perf = manifest.live_performance or {}
        ic_hist = manifest.ic_history or []
        ic_mean = float(perf.get("ic_mean") or (sum(ic_hist) / len(ic_hist) if ic_hist else 0.05))
        proof = self._get_compliance().create_proof(
            factor_id=token_id,
            owner_id=seller_id,
            ic_mean=ic_mean,
            ic_std=float(perf.get("ic_std", 0.12)),
            sharpe=float(perf.get("ir", perf.get("sharpe", 0.8))),
            sample_size=max(len(ic_hist), 30),
        )

        listing = Listing(
            listing_id=f"L{uuid.uuid4().hex[:6].upper()}",
            token_id=token_id,
            seller_id=seller_id,
            reputation_cost=cost,
            signal_count=signal_count,
            diversity_bonus=diversity_bonus,
            zk_proof_hash=proof.proof_hash,
        )
        self._save_listing(listing)
        self._get_compliance().reward_contribution(
            seller_id,
            max(1.0, diversity_bonus * 10),
            f"Listed factor {token_id}",
        )
        return listing

    def contribute(self, listing_id: str, contributor_id: int, quantity: int = 1) -> Order:
        """Spend reputation to access a factor listing (compliance-safe 'purchase')."""
        listing = self._get_listing(listing_id)
        if not listing or not listing.active:
            raise ValueError(f"Listing {listing_id} inactive")
        total_cost = listing.reputation_cost * quantity
        seller_id = listing.seller_id
        if contributor_id == seller_id:
            raise ValueError("Cannot contribute to your own listing")

        compliance = self._get_compliance()
        if not compliance.spend_reputation(contributor_id, total_cost, f"Access {listing_id}"):
            raise ValueError(
                f"Insufficient reputation for user {contributor_id}: need {total_cost}"
            )

        seller_reward = total_cost * self._SELLER_REWARD_RATIO
        seller_reward += listing.diversity_bonus * self._DIVERSITY_BONUS_MULTIPLIER * quantity
        compliance.reward_contribution(seller_id, seller_reward, f"Factor access {listing_id}")

        order = Order(
            order_id=f"O{uuid.uuid4().hex[:8].upper()}",
            listing_id=listing_id,
            buyer_id=contributor_id,
            reputation_spent=total_cost,
            signal_count=listing.signal_count * quantity,
            status="active",
        )
        self._save_order(order)
        return order

    def purchase(self, listing_id: str, buyer_id: int, quantity: int = 1) -> Order:
        """Backward-compatible alias — routes to contribute()."""
        return self.contribute(listing_id, buyer_id, quantity)

    def cancel_order(self, order_id: str, user_id: int) -> bool:
        order = self._get_order(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.status != "active":
            raise ValueError(f"Order {order_id} already {order.status}")
        if order.buyer_id != user_id and user_id != 0:
            raise ValueError("Not authorized to cancel this order")

        compliance = self._get_compliance()
        compliance.reward_contribution(
            order.buyer_id,
            order.reputation_spent,
            f"Cancel refund {order_id}",
        )
        order.status = "cancelled"
        self._rewrite_order(order)
        return True

    def complete_order(self, order_id: str) -> bool:
        order = self._get_order(order_id)
        if not order or order.status != "active":
            return False
        order.status = "completed"
        self._rewrite_order(order)
        return True

    def list_listings(self, *, active_only: bool = True) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self._listing_store.exists():
            return rows
        with self._listing_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if active_only and not data.get("active", True):
                    continue
                row = self._normalize_listing_row(data)
                rows.append(row)
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def list_orders(self, *, buyer_id: int | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not self._order_store.exists():
            return rows
        with self._order_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if buyer_id is not None and int(data.get("buyer_id", -1)) != buyer_id:
                    continue
                row = self._normalize_order_row(data)
                rows.append(row)
        rows.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return rows

    def get_disclosure(self, token_id: str, viewer_id: int, level: str = "low") -> dict[str, Any]:
        disclosure = self._get_compliance().get_disclosure(token_id, viewer_id, level)  # type: ignore[arg-type]
        return disclosure.__dict__

    def deliver_signals(self, order_id: str, signals: list[dict[str, Any]]) -> bool:
        order = self._get_order(order_id)
        if not order or order.status != "active":
            return False
        try:
            path = self._signal_store_root / f"signals_{order_id}.jsonl"
            with path.open("a", encoding="utf-8") as fh:
                for item in signals:
                    delivery = SignalDelivery(
                        delivery_id=item.get("delivery_id") or uuid.uuid4().hex[:12],
                        order_id=order_id,
                        symbol=str(item.get("symbol") or "").strip().upper(),
                        signal_value=float(item.get("signal_value") or 0.0),
                        timestamp=str(item.get("timestamp") or datetime.now(timezone.utc).isoformat()),
                        delivered=True,
                    )
                    fh.write(json.dumps(asdict(delivery), ensure_ascii=False) + "\n")
            self.complete_order(order_id)
            return True
        except Exception as exc:
            logger.warning("Signal delivery for %s failed: %s", order_id, exc)
            return False

    def _compute_listing_diversity(self, token_id: str) -> float:
        existing = self.list_listings(active_only=True)
        factors = [{"factor_id": row.get("token_id", "")} for row in existing]
        factors.append({"factor_id": token_id})
        score = self._get_evolution().compute_diversity(token_id, factors)
        return score.diversity_bonus

    def _normalize_listing_row(self, data: dict[str, Any]) -> dict[str, Any]:
        cost = float(data.get("reputation_cost", data.get("price_tokens", 0)))
        row = dict(data)
        row["reputation_cost"] = cost
        row["price_tokens"] = cost
        row.setdefault("diversity_bonus", 0.0)
        row.setdefault("zk_proof_hash", "")
        return row

    def _normalize_order_row(self, data: dict[str, Any]) -> dict[str, Any]:
        spent = float(data.get("reputation_spent", data.get("tokens_spent", 0)))
        row = dict(data)
        row["reputation_spent"] = spent
        row["tokens_spent"] = spent
        return row

    def _listing_from_row(self, data: dict[str, Any]) -> Listing:
        normalized = self._normalize_listing_row(data)
        return Listing(
            listing_id=normalized["listing_id"],
            token_id=normalized["token_id"],
            seller_id=int(normalized["seller_id"]),
            reputation_cost=float(normalized["reputation_cost"]),
            signal_count=int(normalized.get("signal_count", 100)),
            active=bool(normalized.get("active", True)),
            diversity_bonus=float(normalized.get("diversity_bonus", 0.0)),
            zk_proof_hash=str(normalized.get("zk_proof_hash", "")),
            created_at=str(normalized.get("created_at", "")),
        )

    def _order_from_row(self, data: dict[str, Any]) -> Order:
        normalized = self._normalize_order_row(data)
        return Order(
            order_id=normalized["order_id"],
            listing_id=normalized["listing_id"],
            buyer_id=int(normalized["buyer_id"]),
            reputation_spent=float(normalized["reputation_spent"]),
            signal_count=int(normalized.get("signal_count", 0)),
            status=str(normalized.get("status", "active")),
            created_at=str(normalized.get("created_at", "")),
        )

    def _save_listing(self, listing: Listing) -> None:
        with self._listing_store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(listing), ensure_ascii=False) + "\n")

    def _save_order(self, order: Order) -> None:
        with self._order_store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(order), ensure_ascii=False) + "\n")

    def _get_listing(self, listing_id: str) -> Listing | None:
        if not self._listing_store.exists():
            return None
        with self._listing_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("listing_id") == listing_id:
                    return self._listing_from_row(data)
        return None

    def _get_order(self, order_id: str) -> Order | None:
        if not self._order_store.exists():
            return None
        with self._order_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("order_id") == order_id:
                    return self._order_from_row(data)
        return None

    def _rewrite_order(self, order: Order) -> None:
        if not self._order_store.exists():
            return
        lines: list[str] = []
        with self._order_store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("order_id") == order.order_id:
                    lines.append(json.dumps(asdict(order), ensure_ascii=False))
                else:
                    lines.append(line.rstrip("\n"))
        with self._order_store.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


__all__ = ["AlphaMarketplaceService", "Listing", "Order", "SignalDelivery"]
