"""User access tier snapshot for retail commercialization (Phase D)."""

from __future__ import annotations

from typing import Any

from app.domain.authorization_capabilities import Capability
from app.domain.compliance.retail_manifest import INVESTMENT_DISCLAIMER_SHORT
from app.infrastructure.capabilities.default_policy import (
    FREE_CAPABILITIES,
    PRO_CAPABILITIES,
    capabilities_for_role,
)

_CAPABILITY_LABELS: dict[Capability, str] = {
    Capability.AI_DIAGNOSIS: "AI 诊股",
    Capability.BACKTEST: "策略回测",
    Capability.REALTIME_ALERT: "实时预警",
    Capability.QLIB: "Qlib 高级回测",
    Capability.PORTFOLIO_MANAGE: "组合管理",
    Capability.SIGNAL_FLAG: "信号旗手",
    Capability.INVESTMENT_MANAGER: "投资经理",
    Capability.RESEARCH_REPORT: "研究报告",
    Capability.DATA_BACKFILL: "数据回补",
    Capability.SYSTEM_CONFIG: "系统配置",
    Capability.USER_MANAGE: "用户管理",
}

_TIER_LABELS = {
    "free": "免费版",
    "pro": "专业版",
    "admin": "管理员",
}


def _normalize_tier(role: str) -> str:
    role_l = (role or "free").lower()
    if role_l in ("admin", "administrator"):
        return "admin"
    if role_l in ("pro", "vip", "premium"):
        return "pro"
    return "free"


class UserAccessPolicyService:
    """Expose tier, limits, and upgrade hints for profile / retail assistant UI."""

    def snapshot_for_user(self, user: Any) -> dict[str, Any]:
        role = str(getattr(user, "role", None) or "free")
        tier = _normalize_tier(role)
        enabled_caps = capabilities_for_role(role)

        features: list[dict[str, Any]] = [
            {
                "id": cap.value,
                "name": _CAPABILITY_LABELS.get(cap, cap.value),
                "enabled": True,
            }
            for cap in sorted(enabled_caps, key=lambda c: c.value)
        ]

        if tier == "free":
            for cap in sorted(PRO_CAPABILITIES - FREE_CAPABILITIES, key=lambda c: c.value):
                if cap in enabled_caps:
                    continue
                features.append(
                    {
                        "id": cap.value,
                        "name": _CAPABILITY_LABELS.get(cap, cap.value),
                        "enabled": False,
                    }
                )

        limits = {
            "ai_diagnosis_daily": 5 if tier == "free" else 50 if tier == "pro" else 999,
            "watchlist_groups": 1 if tier == "free" else 10 if tier == "pro" else 99,
            "decision_review_queue": 20 if tier == "free" else 200,
        }

        return {
            "tier": tier,
            "tier_label": _TIER_LABELS.get(tier, tier),
            "role": role,
            "features": features,
            "limits": limits,
            "upgrade_hints": self._upgrade_hints(tier),
            "disclaimer": INVESTMENT_DISCLAIMER_SHORT,
        }

    def _upgrade_hints(self, tier: str) -> list[str]:
        if tier == "free":
            return [
                "升级专业版可解锁 AI 深度研报、Qlib 回测与组合压力测试",
                "人工决策复核队列在专业版享有更高容量",
            ]
        if tier == "pro":
            return ["如需 API 访问与团队席位，请联系机构白名单"]
        return ["管理员拥有全部能力，请遵守内控与合规流程"]
