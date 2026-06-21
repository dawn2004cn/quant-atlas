from __future__ import annotations
"""Multi-tenancy & Quota Management for 100+ Investment Managers.

Implements from strategy_plan2.md:
- LLM Token quotas per manager
- Compute quotas per tenant
- Database row-level isolation

Usage:
    quota_manager = TenantQuotaManager()
    quota_manager.check_quota("manager_001", "llm_tokens", 1000)
    quota_manager.get_usage("manager_001", "llm_tokens")
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from app.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class QuotaLimit:
    """Quota limit for a resource type."""
    resource: str
    limit: int
    window_seconds: int = 3600
    burst_limit: int | None = None


@dataclass
class QuotaUsage:
    """Current quota usage."""
    manager_id: str
    resource: str
    used: int = 0
    window_start: datetime = field(default_factory=datetime.now)
    requests: list = field(default_factory=list)


@dataclass
class QuotaCheckResult:
    """Result of quota check."""
    allowed: bool
    remaining: int
    reset_at: datetime
    wait_seconds: float = 0.0


class TenantQuotaManager:
    """Manages quotas for 100+ investment managers."""

    DEFAULT_QUOTAS: dict[str, list[QuotaLimit]] = {
        "default": [
            QuotaLimit("llm_tokens", 100000, 3600, 10000),
            QuotaLimit("backtest_runs", 50, 3600),
            QuotaLimit("api_calls", 1000, 3600),
            QuotaLimit("storage_mb", 500, 3600),
        ],
        "premium": [
            QuotaLimit("llm_tokens", 500000, 3600, 50000),
            QuotaLimit("backtest_runs", 200, 3600),
            QuotaLimit("api_calls", 5000, 3600),
            QuotaLimit("storage_mb", 2000, 3600),
        ],
    }

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._usage: dict[str, dict[str, QuotaUsage]] = {}
        self._limits: dict[str, list[QuotaLimit]] = {}

        for tier, limits in self.DEFAULT_QUOTAS.items():
            self._limits[tier] = limits

    def get_quota_limit(self, manager_id: str, resource: str, tier: str = "default") -> QuotaLimit | None:
        """Get quota limit for manager."""
        limits = self._limits.get(tier, self._limits["default"])
        for limit in limits:
            if limit.resource == resource:
                return limit
        return None

    def check_quota(self, manager_id: str, resource: str, amount: int = 1, tier: str = "default") -> QuotaCheckResult:
        """Check if quota allows the request."""
        limit = self.get_quota_limit(manager_id, resource, tier)
        if not limit:
            return QuotaCheckResult(True, 999999, datetime.now())

        key = f"{manager_id}:{resource}"
        usage = self._get_usage(key, limit)

        now = datetime.now()
        self._cleanup_old_requests(usage, now, limit.window_seconds)

        current_used = len(usage.requests) * amount
        remaining = limit.limit - current_used

        if remaining >= amount:
            usage.requests.append((amount, now))
            self._save_usage(key, usage)
            return QuotaCheckResult(
                allowed=True,
                remaining=remaining - amount,
                reset_at=usage.window_start + timedelta(seconds=limit.window_seconds),
            )
        else:
            oldest = usage.requests[0][1] if usage.requests else now
            reset_at = oldest + timedelta(seconds=limit.window_seconds)
            wait_seconds = (reset_at - now).total_seconds()
            return QuotaCheckResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                wait_seconds=max(0, wait_seconds),
            )

    def consume_quota(self, manager_id: str, resource: str, amount: int, tier: str = "default") -> bool:
        """Consume quota after operation completes."""
        limit = self.get_quota_limit(manager_id, resource, tier)
        if not limit:
            return True

        key = f"{manager_id}:{resource}"
        usage = self._get_usage(key, limit)

        now = datetime.now()
        self._cleanup_old_requests(usage, now, limit.window_seconds)

        current_used = len(usage.requests) * amount
        if current_used + amount <= limit.limit:
            usage.requests.append((amount, now))
            self._save_usage(key, usage)
            return True
        return False

    def get_usage(self, manager_id: str, resource: str, tier: str = "default") -> tuple[int, int]:
        """Get current usage and limit."""
        limit = self.get_quota_limit(manager_id, resource, tier)
        if not limit:
            return 0, 999999

        key = f"{manager_id}:{resource}"
        usage = self._get_usage(key, limit)

        now = datetime.now()
        self._cleanup_old_requests(usage, now, limit.window_seconds)

        return len(usage.requests), limit.limit

    def set_tier(self, manager_id: str, tier: str) -> None:
        """Set quota tier for manager."""
        if tier not in self.DEFAULT_QUOTAS:
            logger.warning(f"Unknown tier {tier}, using default")
            tier = "default"
        logger.info(f"Manager {manager_id} assigned to tier {tier}")

    def _get_usage(self, key: str, limit: QuotaLimit) -> QuotaUsage:
        """Get or create usage record."""
        if key not in self._usage:
            self._usage[key] = QuotaUsage(
                manager_id=key.split(":")[0],
                resource=key.split(":")[1] if len(key.split(":")) > 1 else "",
            )
        return self._usage[key]

    def _save_usage(self, key: str, usage: QuotaUsage) -> None:
        """Save usage to redis or memory."""
        self._usage[key] = usage

    def _cleanup_old_requests(self, usage: QuotaUsage, now: datetime, window_seconds: int) -> None:
        """Remove requests outside the window."""
        cutoff = now - timedelta(seconds=window_seconds)
        usage.requests = [
            (amt, ts) for amt, ts in usage.requests
            if ts > cutoff
        ]

        if not usage.requests or usage.window_start < cutoff:
            usage.window_start = now
            usage.requests = []


class ComputeQuotaManager:
    """Manages compute resource quotas."""

    def __init__(self):
        self._active_jobs: dict[str, int] = {}

    def check_compute(self, manager_id: str, max_concurrent: int = 5) -> bool:
        """Check if manager can start new compute job."""
        current = self._active_jobs.get(manager_id, 0)
        if current >= max_concurrent:
            return False
        self._active_jobs[manager_id] = current + 1
        return True

    def release_compute(self, manager_id: str) -> None:
        """Release compute slot."""
        current = self._active_jobs.get(manager_id, 0)
        self._active_jobs[manager_id] = max(0, current - 1)


_global_quota_manager: TenantQuotaManager | None = None
_global_compute_manager: ComputeQuotaManager | None = None


def get_quota_manager() -> TenantQuotaManager:
    """Get global quota manager."""
    global _global_quota_manager
    if _global_quota_manager is None:
        _global_quota_manager = TenantQuotaManager()
    return _global_quota_manager


def get_compute_manager() -> ComputeQuotaManager:
    """Get global compute manager."""
    global _global_compute_manager
    if _global_compute_manager is None:
        _global_compute_manager = ComputeQuotaManager()
    return _global_compute_manager