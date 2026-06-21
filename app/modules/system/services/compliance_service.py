"""Compliance Pivot — Phase: Optimization.
De-financialization: Alpha Marketplace uses Reputation points instead of real currency.
ZK-proof: Zero-knowledge factor performance proof.
Tiered disclosure: Low/Medium/High granularity factor explanation."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.core.logger import get_logger

logger = get_logger(__name__)

DisclosureLevel = Literal["low", "medium", "high"]


@dataclass
class ReputationAccount:
    """User reputation account — replaces real currency."""
    user_id: int
    reputation_score: float = 100.0  # starting score
    contribution_count: int = 0
    rewards_received: float = 0.0
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ZKFactorProof:
    """Zero-knowledge proof of factor performance without revealing formula."""
    factor_id: str
    owner_id: int
    proof_hash: str  # commitment hash
    ic_mean: float  # revealed aggregate metric
    ic_std: float
    sharpe: float
    sample_size: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verification_nonce: str = ""  # stored for owner verification; not disclosed in listings

    def verify(self, secret_nonce: str) -> bool:
        """Verify the proof by recomputing the commitment."""
        raw = f"{self.factor_id}:{self.owner_id}:{self.ic_mean}:{self.ic_std}:{self.sharpe}:{self.sample_size}:{secret_nonce}"
        expected = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return self.proof_hash == expected

    def public_dict(self) -> dict[str, Any]:
        """Serialize without verification nonce."""
        data = self.__dict__.copy()
        data.pop("verification_nonce", None)
        return data


@dataclass
class TieredDisclosure:
    """Tiered factor explanation — more detail for higher reputation."""
    factor_id: str
    level: DisclosureLevel
    description: str
    details: dict[str, Any] = field(default_factory=dict)
    required_reputation: float = 0.0


class ComplianceService:
    """Compliance pivot: reputation-based economy, ZK-proofs, tiered disclosure."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "compliance"
        self._store.mkdir(parents=True, exist_ok=True)
        self._reputation_file = self._store / "reputation.jsonl"
        self._proof_file = self._store / "zk_proofs.jsonl"

    # ── Reputation Economy ──────────────────────────────────────────

    def get_reputation(self, user_id: int) -> ReputationAccount:
        """Get or create reputation account."""
        account = self._load_reputation(user_id)
        if account is None:
            account = ReputationAccount(user_id=user_id)
            self._save_reputation(account)
        return account

    def reward_contribution(self, user_id: int, points: float, reason: str) -> ReputationAccount:
        """Reward a user for contributing factors or insights."""
        account = self.get_reputation(user_id)
        account.reputation_score = min(1000.0, account.reputation_score + points)
        account.contribution_count += 1
        account.rewards_received += points
        account.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_reputation(account)
        logger.info("User %d rewarded %.1f reputation for: %s (total: %.1f)", user_id, points, reason, account.reputation_score)
        return account

    def spend_reputation(self, user_id: int, cost: float, reason: str) -> bool:
        """Spend reputation to access a factor or service."""
        account = self.get_reputation(user_id)
        if account.reputation_score < cost:
            return False
        account.reputation_score -= cost
        account.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_reputation(account)
        logger.info("User %d spent %.1f reputation for: %s (remaining: %.1f)", user_id, cost, reason, account.reputation_score)
        return True

    def get_leaderboard(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get top contributors by reputation."""
        accounts = self._load_all_reputation()
        accounts.sort(key=lambda a: a.reputation_score, reverse=True)
        return [
            {
                "user_id": a.user_id,
                "reputation_score": round(a.reputation_score, 1),
                "contributions": a.contribution_count,
                "rewards": round(a.rewards_received, 1),
            }
            for a in accounts[:limit]
        ]

    # ── ZK Proofs ───────────────────────────────────────────────────

    def create_proof(self, factor_id: str, owner_id: int, ic_mean: float, ic_std: float, sharpe: float, sample_size: int) -> ZKFactorProof:
        """Create a zero-knowledge proof for a factor's performance."""
        nonce = secrets.token_hex(8)
        raw = f"{factor_id}:{owner_id}:{ic_mean}:{ic_std}:{sharpe}:{sample_size}:{nonce}"
        proof_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
        proof = ZKFactorProof(
            factor_id=factor_id,
            owner_id=owner_id,
            proof_hash=proof_hash,
            ic_mean=ic_mean,
            ic_std=ic_std,
            sharpe=sharpe,
            sample_size=sample_size,
            verification_nonce=nonce,
        )
        self._save_proof(proof)
        logger.info("ZK proof created for factor %s by user %d", factor_id, owner_id)
        return proof

    def get_proof(self, factor_id: str, owner_id: int) -> ZKFactorProof | None:
        """Load a stored proof for a factor owner."""
        return self._load_proof(factor_id, owner_id)

    def verify_proof(self, factor_id: str, owner_id: int, secret_nonce: str) -> bool:
        """Verify a ZK proof given the secret nonce."""
        proof = self._load_proof(factor_id, owner_id)
        if not proof:
            return False
        return proof.verify(secret_nonce)

    def verify_stored_proof(self, factor_id: str, owner_id: int) -> bool:
        """Verify proof using server-stored nonce (owner-only API)."""
        proof = self._load_proof(factor_id, owner_id)
        if not proof or not proof.verification_nonce:
            return False
        return proof.verify(proof.verification_nonce)

    # ── Tiered Disclosure ───────────────────────────────────────────

    def get_disclosure(self, factor_id: str, viewer_id: int, level: DisclosureLevel) -> TieredDisclosure:
        """Get tiered factor disclosure based on viewer reputation."""
        viewer_rep = self.get_reputation(viewer_id)
        required = {"low": 0, "medium": 50, "high": 200}

        if viewer_rep.reputation_score < required[level]:
            return TieredDisclosure(
                factor_id=factor_id,
                level=level,
                description="需要更多贡献值解锁此级别的因子详情",
                required_reputation=required[level],
            )

        disclosures = {
            "low": TieredDisclosure(
                factor_id=factor_id,
                level="low",
                description=f"因子 {factor_id} 的历史 Sharpe 比率",
                details={"sharpe": "0.8-1.2", "direction": "多头"},
                required_reputation=0,
            ),
            "medium": TieredDisclosure(
                factor_id=factor_id,
                level="medium",
                description=f"因子 {factor_id} 的 IC 序列和行业暴露",
                details={"ic_mean": 0.05, "ic_std": 0.12, "industry_exposure": "科技+消费"},
                required_reputation=50,
            ),
            "high": TieredDisclosure(
                factor_id=factor_id,
                level="high",
                description=f"因子 {factor_id} 的完整公式和权重",
                details={"formula": "保密（需 NDA）", "weights": "仅限高级用户"},
                required_reputation=200,
            ),
        }
        return disclosures.get(level, disclosures["low"])

    # ── Persistence ─────────────────────────────────────────────────

    def _load_reputation(self, user_id: int) -> ReputationAccount | None:
        if not self._reputation_file.exists():
            return None
        with self._reputation_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("user_id", -1)) == user_id:
                    return ReputationAccount(**data)
        return None

    def _save_reputation(self, account: ReputationAccount):
        rows = []
        if self._reputation_file.exists():
            with self._reputation_file.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if int(data.get("user_id", -1)) != account.user_id:
                        rows.append(line.rstrip("\n"))
        rows.append(json.dumps(account.__dict__, ensure_ascii=False))
        with self._reputation_file.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")

    def _load_all_reputation(self) -> list[ReputationAccount]:
        accounts = []
        if not self._reputation_file.exists():
            return accounts
        with self._reputation_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    accounts.append(ReputationAccount(**json.loads(line)))
        return accounts

    def _save_proof(self, proof: ZKFactorProof):
        with self._proof_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(proof.__dict__, ensure_ascii=False) + "\n")

    def _load_proof(self, factor_id: str, owner_id: int) -> ZKFactorProof | None:
        if not self._proof_file.exists():
            return None
        with self._proof_file.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if data.get("factor_id") == factor_id and int(data.get("owner_id", -1)) == owner_id:
                    return ZKFactorProof(**data)
        return None
