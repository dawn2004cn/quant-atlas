from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CopyTradeSubscription:
    subscription_id: str
    follower_id: int
    provider_id: int
    provider_name: str
    allocation_pct: float = 10.0
    active: bool = True


@dataclass
class CopyTradeSignal:
    signal_id: str
    provider_id: int
    symbol: str
    action: str
    quantity: int
    price: float


class CopyTradingService:
    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "copy_trading"
        self._store.mkdir(parents=True, exist_ok=True)
        self._subs_file = self._store / "subscriptions.jsonl"
        self._signals_file = self._store / "signals.jsonl"

    def subscribe(self, follower_id: int, provider_id: int, provider_name: str, allocation_pct: float = 10.0) -> CopyTradeSubscription:
        sub = CopyTradeSubscription(
            subscription_id=f"ct.{uuid.uuid4().hex[:8]}",
            follower_id=follower_id,
            provider_id=provider_id,
            provider_name=provider_name,
            allocation_pct=min(100, max(1, allocation_pct)),
        )
        self._save_subscription(sub)
        logger.info("User %d subscribed to provider %s (%.1f%%)", follower_id, provider_name, allocation_pct)
        return sub

    def unsubscribe(self, subscription_id: str) -> bool:
        subs = self._load_subscriptions()
        for sub in subs:
            if sub.subscription_id == subscription_id:
                sub.active = False
                self._save_all_subscriptions(subs)
                return True
        return False

    def publish_signal(self, provider_id: int, symbol: str, action: str, quantity: int, price: float) -> CopyTradeSignal:
        signal = CopyTradeSignal(
            signal_id=f"sig.{uuid.uuid4().hex[:8]}",
            provider_id=provider_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
        )
        self._save_signal(signal)
        followers = self._get_followers(provider_id)
        if followers:
            try:
                from app.core.dual_path_router import PathPriority, PathTask, PathType, get_dual_path_router
                router = get_dual_path_router()
                for sub in followers:
                    scaled_qty = max(1, int(quantity * sub.allocation_pct / 100))
                    task = PathTask(
                        task_id=f"ct.{signal.signal_id}.{sub.follower_id}",
                        path=PathType.FAST,
                        priority=PathPriority.HIGH,
                        handler="copy_trade_execute",
                        payload={
                            "follower_id": sub.follower_id,
                            "symbol": symbol,
                            "action": action,
                            "quantity": scaled_qty,
                            "price": price,
                            "portfolio_value": 1_000_000,
                        },
                        max_latency_ms=100,
                    )
                    router.route_fast(task)
            except Exception as exc:
                logger.warning("Fast Path copy-trade dispatch failed, logging only: %s", exc)
                for sub in followers:
                    scaled_qty = max(1, int(quantity * sub.allocation_pct / 100))
                    logger.info("Copy-trade: User %d → %s %d shares of %s (scaled from %d)", sub.follower_id, action, scaled_qty, symbol, quantity)
        return signal

    def get_subscriptions(self, user_id: int) -> list[CopyTradeSubscription]:
        return [s for s in self._load_subscriptions() if s.follower_id == user_id]

    def _get_followers(self, provider_id: int) -> list[CopyTradeSubscription]:
        return [s for s in self._load_subscriptions() if s.provider_id == provider_id and s.active]

    def _save_subscription(self, sub: CopyTradeSubscription):
        with self._subs_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(sub.__dict__, ensure_ascii=False) + "\n")

    def _save_all_subscriptions(self, subs: list[CopyTradeSubscription]):
        with self._subs_file.open("w", encoding="utf-8") as fh:
            for s in subs:
                fh.write(json.dumps(s.__dict__, ensure_ascii=False) + "\n")

    def _load_subscriptions(self) -> list[CopyTradeSubscription]:
        if not self._subs_file.exists():
            return []
        subs = []
        with self._subs_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    subs.append(CopyTradeSubscription(**json.loads(line)))
        return subs

    def _save_signal(self, signal: CopyTradeSignal):
        with self._signals_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(signal.__dict__, ensure_ascii=False) + "\n")

    def get_provider_rating(self, provider_id):
        signals = []
        if self._signals_file.exists():
            with self._signals_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    sig = json.loads(line)
                    if sig.get("provider_id") == provider_id:
                        signals.append(sig)
        total = len(signals)
        if total == 0:
            return {"provider_id": provider_id, "total_signals": 0, "rating": "unrated"}
        wins = [s for s in signals if s.get("outcome") == "win"]
        win_rate = len(wins) / total
        recent = signals[-20:]
        recent_wins = sum(1 for s in recent if s.get("outcome") == "win")
        recent_win_rate = recent_wins / max(len(recent), 1)
        if win_rate >= 0.6 and recent_win_rate >= 0.55:
            rating = "A"
        elif win_rate >= 0.5:
            rating = "B"
        elif win_rate >= 0.4:
            rating = "C"
        else:
            rating = "D"
        return {
            "provider_id": provider_id,
            "total_signals": total,
            "win_rate": round(win_rate, 4),
            "recent_win_rate": round(recent_win_rate, 4),
            "rating": rating,
            "total_wins": len(wins),
            "total_losses": total - len(wins),
        }

    def get_follower_portfolio(self, follower_id):
        subs = self.get_subscriptions(follower_id)
        if not subs:
            return {"follower_id": follower_id, "providers": [], "total_value": 0.0}
        provider_ids = {s.provider_id for s in subs}
        signals_by_pid = {}
        if self._signals_file.exists():
            with self._signals_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    sig = json.loads(line)
                    pid = sig.get("provider_id")
                    if pid in provider_ids:
                        signals_by_pid.setdefault(pid, []).append(sig)
        providers = []
        total_value = 0.0
        for sub in subs:
            sigs = signals_by_pid.get(sub.provider_id, [])
            open_pos = [s for s in sigs if s.get("status") == "open"]
            pos_val = sum(s.get("quantity", 0) * s.get("price", 0) * sub.allocation_pct / 100 for s in open_pos)
            total_value += pos_val
            providers.append({
                "provider_id": sub.provider_id,
                "provider_name": sub.provider_name,
                "allocation_pct": sub.allocation_pct,
                "active_signals": len(open_pos),
                "position_value": round(pos_val, 2),
            })
        return {
            "follower_id": follower_id,
            "providers": providers,
            "total_providers": len(providers),
            "total_value": round(total_value, 2),
        }
