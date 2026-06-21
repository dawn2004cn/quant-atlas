"""Retail billing placeholder — Stripe integration deferred to post-Beta (Phase E)."""

from __future__ import annotations

from typing import Any


def build_billing_status(user: Any | None = None) -> dict[str, Any]:
    """Return non-charging Beta billing surface for profile / upgrade CTAs."""
    role = str(getattr(user, "role", None) or "free").lower()
    tier = "pro" if role in ("pro", "vip", "premium") else "admin" if role in ("admin", "administrator") else "free"
    return {
        "enabled": False,
        "provider": "stripe",
        "mode": "beta",
        "tier": tier,
        "checkout_available": False,
        "message": "订阅计费即将上线，当前内测阶段免费使用核心研究能力。",
        "upgrade_hints": [
            "专业版将包含 Qlib 高级回测、组合压力测试与 API 访问",
            "机构客户请联系白名单开通",
        ],
    }
