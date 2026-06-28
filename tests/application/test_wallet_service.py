"""Regression tests for WalletService (Phase 16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.system.services.alpha.wallet_service import WalletEntry, WalletService


@pytest.fixture
def wallet(tmp_path: Path) -> WalletService:
    return WalletService(store_path=tmp_path / "wallet.jsonl")


class TestWalletService:
    """Token wallet operations."""

    def test_new_user_balance_zero(self, wallet: WalletService):
        assert wallet.get_balance(1) == 0.0

    def test_credit_increases_balance(self, wallet: WalletService):
        wallet.credit(1, 100.0, "initial deposit")
        assert wallet.get_balance(1) == 100.0

    def test_debit_decreases_balance(self, wallet: WalletService):
        wallet.credit(1, 100.0, "deposit")
        wallet.debit(1, 30.0, "purchase")
        assert wallet.get_balance(1) == 70.0

    def test_credit_negative_raises(self, wallet: WalletService):
        with pytest.raises(ValueError, match="positive"):
            wallet.credit(1, -50.0)

    def test_credit_zero_raises(self, wallet: WalletService):
        with pytest.raises(ValueError, match="positive"):
            wallet.credit(1, 0.0)

    def test_debit_negative_raises(self, wallet: WalletService):
        with pytest.raises(ValueError, match="positive"):
            wallet.debit(1, -10.0)

    def test_debit_insufficient_balance_raises(self, wallet: WalletService):
        wallet.credit(1, 10.0, "deposit")
        with pytest.raises(ValueError, match="Insufficient"):
            wallet.debit(1, 20.0)

    def test_transfer_moves_balance(self, wallet: WalletService):
        wallet.credit(1, 100.0, "deposit")
        wallet.transfer(1, 2, 40.0, "payment")
        assert wallet.get_balance(1) == 60.0
        assert wallet.get_balance(2) == 40.0

    def test_transfer_insufficient_raises(self, wallet: WalletService):
        wallet.credit(1, 10.0, "deposit")
        with pytest.raises(ValueError, match="Insufficient"):
            wallet.transfer(1, 2, 20.0)

    def test_multiple_credits_accumulate(self, wallet: WalletService):
        wallet.credit(1, 50.0)
        wallet.credit(1, 50.0)
        wallet.credit(1, 50.0)
        assert wallet.get_balance(1) == 150.0

    def test_persistence_across_instances(self, tmp_path: Path):
        store = tmp_path / "wallet.jsonl"
        w1 = WalletService(store_path=store)
        w1.credit(42, 200.0, "test")

        w2 = WalletService(store_path=store)
        assert w2.get_balance(42) == 200.0

    def test_multiple_users_independent(self, wallet: WalletService):
        wallet.credit(1, 100.0)
        wallet.credit(2, 200.0)
        assert wallet.get_balance(1) == 100.0
        assert wallet.get_balance(2) == 200.0

    def test_wallet_entry_dataclass(self):
        entry = WalletEntry(user_id=5, balance=500.0, updated_at="2026-01-01T00:00:00")
        assert entry.user_id == 5
        assert entry.balance == 500.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
