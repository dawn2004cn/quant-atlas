"""Exchange API key permission policy (SRS: no withdraw)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.core.logger import get_logger

logger = get_logger(__name__)


class ExchangeApiKeyPolicyError(ValueError):
    """Raised when exchange config enables withdraw or violates policy."""


@dataclass(frozen=True, slots=True)
class ApiKeyPolicy:
    allow_trade: bool = True
    allow_read: bool = True
    allow_withdraw: bool = False


DEFAULT_POLICY = ApiKeyPolicy()


def assert_no_withdraw(config: Mapping[str, Any] | None, *, exchange_id: str = "") -> ApiKeyPolicy:
    """Reject configs that explicitly enable withdraw.

    Recognized keys (truthy → reject): ``enable_withdraw``, ``allow_withdraw``,
    ``withdraw``, ``enableWithdraw``.
    """
    cfg = dict(config or {})
    flags = (
        cfg.get("enable_withdraw"),
        cfg.get("allow_withdraw"),
        cfg.get("withdraw"),
        cfg.get("enableWithdraw"),
    )
    if any(bool(x) for x in flags if x is not None):
        label = exchange_id or str(cfg.get("exchange_id") or "exchange")
        logger.error("exchange_api_key_policy reject withdraw enabled exchange=%s", label)
        raise ExchangeApiKeyPolicyError(f"withdraw_forbidden:{label}")
    # Cannot remotely verify exchange-side permissions; audit assumption.
    if cfg.get("assumed_no_withdraw") is False:
        raise ExchangeApiKeyPolicyError(f"assumed_no_withdraw_required:{exchange_id or 'exchange'}")
    logger.info(
        "exchange_api_key_policy ok exchange=%s allow_trade=%s allow_read=%s allow_withdraw=False",
        exchange_id or cfg.get("exchange_id") or "exchange",
        True,
        True,
    )
    return DEFAULT_POLICY
