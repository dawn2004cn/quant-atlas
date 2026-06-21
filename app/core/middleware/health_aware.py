"""Health-aware user messaging for proactive intelligence (Phase 4)."""

from __future__ import annotations

from app.core.middleware.degraded_context import get_degraded_reasons, is_system_degraded
from app.domain.dto.decision_context_dto import DecisionContextDTO

_REASON_LABELS: dict[str, str] = {
    "tencent_quotes": "腾讯行情源",
    "openbb": "OpenBB 数据",
    "ollama": "本地 LLM",
    "ollama_generate": "本地 LLM",
    "fingpt": "FinGPT 情感模型",
    "tdx_legacy": "通达信网关",
    "market_l2_cache": "本地缓存行情",
    "market_tencent_fallback": "腾讯行情",
    "market_yfinance_fallback": "YFinance 备用源",
    "market_hk_circuit": "港股主源",
}


def build_degraded_user_message(reasons: list[str] | None = None) -> str:
    """Human-readable notice when the system is in degraded mode."""
    labels = []
    for raw in reasons or get_degraded_reasons():
        key = str(raw).split("_")[0] if raw else ""
        label = _REASON_LABELS.get(str(raw), str(raw))
        if label and label not in labels:
            labels.append(label)
    if not labels:
        return "系统处于降级模式，部分深度因子分析已替换为基础统计模型。"
    joined = "、".join(labels[:4])
    return f"由于数据源降级（{joined}），部分深度因子分析已替换为基础统计模型。"


def append_health_notice(decision: DecisionContextDTO) -> DecisionContextDTO:
    """Attach degraded-mode notice to a decision DTO for Jarvis / AI surfaces."""
    if not is_system_degraded():
        return decision
    notice = build_degraded_user_message()
    snapshot = dict(decision.input_snapshot)
    snapshot["system_notice"] = notice
    trace = list(decision.reasoning_trace)
    if notice not in trace:
        trace.append(notice)
    return decision.model_copy(update={"input_snapshot": snapshot, "reasoning_trace": trace})


__all__ = ["build_degraded_user_message", "append_health_notice", "is_system_degraded"]
