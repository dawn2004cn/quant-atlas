"""Retail compliance copy and beta SLA targets (Phase D)."""

from __future__ import annotations

from typing import Any

MANIFEST_VERSION = "2026-06-16"

INVESTMENT_DISCLAIMER_SHORT = (
    "本平台展示的数据、指标与 AI 生成内容仅供学习研究，不构成证券投资建议。"
    "请独立判断并自担风险。"
)

INVESTMENT_DISCLAIMER_FULL = (
    "Quant Atlas 是量化研究与信号辅助工具，不提供证券投资顾问服务，"
    "不代客理财，不承诺收益。历史回测与模拟结果不代表未来表现。"
    "AI 输出可能存在幻觉或数据延迟，请勿作为唯一决策依据。"
    "行情与财务数据可能存在延迟或误差，请以交易所及官方披露为准。"
)

PRIVACY_NOTICE = (
    "我们按最小必要原则处理账户、自选、操作审计等数据；"
    "可在个人中心申请导出或删除（Beta 阶段部分能力为占位）。"
)

BETA_SLA: dict[str, Any] = {
    "tier": "beta",
    "uptime_target_pct": 99.0,
    "api_p95_ms": 2000,
    "decision_review_sla_hours": 24,
    "data_freshness_minutes": {
        "CN_quote": 15,
        "CN_fundamental": 1440,
    },
    "support_channels": ["站内消息", "GitHub Issues"],
    "exclusions": [
        "第三方行情源中断",
        "用户本地网络故障",
        "计划内维护窗口",
    ],
}


def build_compliance_manifest() -> dict[str, Any]:
    return {
        "version": MANIFEST_VERSION,
        "product_positioning": "A 股零售量化研究与信号辅助平台（非投顾）",
        "disclaimers": {
            "short": INVESTMENT_DISCLAIMER_SHORT,
            "full": INVESTMENT_DISCLAIMER_FULL,
            "privacy": PRIVACY_NOTICE,
        },
        "sla": BETA_SLA,
        "links": {
            "privacy_api": "/api/v1/user/privacy-consent",
            "access_policy_api": "/api/v1/user/access-policy",
            "health_api": "/api/v1/system/health",
        },
    }
