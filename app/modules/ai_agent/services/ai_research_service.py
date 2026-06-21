from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""TradingAgents 研究流程的应用层封装（供 Flask API 调用）。"""


import threading
from datetime import datetime
from typing import Any

from app.core.base_service import BaseApplicationService
from app.domain.ports.research_port import ResearchPort
from .fingpt_application_service import FinGPTApplicationService

_AGENT_SOURCE_KEYS: tuple[tuple[str, str], ...] = (
    ("macro", "macro_analyst"),
    ("fundamental", "fundamental_analyst"),
    ("technical", "technical_analyst"),
    ("sentiment", "sentiment_analyst"),
    ("backtest_optimizer", "backtest_optimizer"),
    ("risk_manager", "risk_manager"),
)


def _confidence_from_reports(analyst_reports: dict[str, Any]) -> float:
    filled = 0
    for src, _ in _AGENT_SOURCE_KEYS:
        v = analyst_reports.get(src)
        if isinstance(v, str) and len(v.strip()) > 80:
            filled += 1
    return round(min(0.95, 0.45 + 0.07 * filled), 2)


def _overall_summary(raw: dict[str, Any]) -> str:
    if not raw.get("ok"):
        err = raw.get("error") or "unknown"
        msg = raw.get("message") or ""
        return f"研究未完成：{err}" + (f" — {msg}" if msg else "")

    sup = str(raw.get("supervisor_memo") or "").strip()
    reps = raw.get("analyst_reports") or {}
    risk_tail = str(reps.get("risk_manager") or "").strip()
    if len(risk_tail) > 2000:
        risk_tail = risk_tail[:2000] + "\n…（截断）"

    parts: list[str] = []
    if sup:
        parts.append("## Supervisor 摘要\n" + sup)
    if risk_tail:
        parts.append("## 风险管理结论摘录\n" + risk_tail)
    if not parts:
        return str(raw.get("full_report_markdown") or "")[:4000]
    return "\n\n".join(parts)


def _default_recommendations(raw: dict[str, Any]) -> list[str]:
    base = [
        "加入自选股",
        "导出策略代码（在回测模块中对照报告中的策略名与参数）",
    ]
    if not raw.get("ok"):
        return ["检查 ticker / user_id / LLM 与 quant_tools 配置后重试"]
    risk_txt = str((raw.get("analyst_reports") or {}).get("risk_manager") or "")
    if any(k in risk_txt for k in ("仓位", "杠杆", "止损")):
        base.append("按风险管理段落复核仓位与止损规则后再下单")
    return base


def build_ai_research_response(raw: dict[str, Any]) -> GenericResponseDTO:
    """
    将 ``TradingAgentsService.run_research`` / ``app.agents.research.package_full_report`` 的 dict
    映射为对外统一 JSON 形状。
    """
    analyst_src = raw.get("analyst_reports") if isinstance(raw.get("analyst_reports"), dict) else {}
    agent_reports: dict[str, str] = {}
    for src, api_key in _AGENT_SOURCE_KEYS:
        v = analyst_src.get(src, "")
        agent_reports[api_key] = v if isinstance(v, str) else str(v)

    backtest_results: dict[str, Any] = {
        "narrative": agent_reports["backtest_optimizer"],
        "strategy_catalog_hint": raw.get("registered_strategies_used_hint") or "",
    }

    risk_assessment: dict[str, Any] = {
        "risk_manager": agent_reports["risk_manager"],
        "investment_debate": raw.get("investment_debate") or {},
        "risk_debate": raw.get("risk_debate") or {},
    }

    return {
        "ok": bool(raw.get("ok")),
        "error": raw.get("error"),
        "message": raw.get("message"),
        "ticker": raw.get("ticker"),
        "query": raw.get("query"),
        "user_id": raw.get("user_id"),
        "thread_id": raw.get("thread_id"),
        "overall_summary": _overall_summary(raw),
        "agent_reports": agent_reports,
        "backtest_results": backtest_results,
        "risk_assessment": risk_assessment,
        "recommendations": _default_recommendations(raw),
        "confidence_score": 0.0 if not raw.get("ok") else _confidence_from_reports(analyst_src),
    }


class AiResearchService(BaseApplicationService):
    """
    通过 ``ResearchPort`` 委托多智能体研究（默认 ``TradingAgentsResearchAdapter``）。

    进程启动须已完成 ``configure_quant_tools()``（见 ``bootstrap``）。
    """

    def __init__(
        self,
        fingpt_application_service: FinGPTApplicationService | None = None,
        *,
        research_port: ResearchPort | None = None,
    ) -> None:
        super().__init__()
        self._fingpt_application_service = fingpt_application_service
        self._research_port = research_port
        self._chat_history: dict[str, list[dict[str, Any]]] = {}
        self._chat_history_lock = threading.Lock()

    def _resolve_research_port(self) -> ResearchPort:
        if self._research_port is not None:
            return self._research_port
        from app.modules.system.services.helpers.research_access import create_trading_agents_research_port

        self._research_port = create_trading_agents_research_port(
            fingpt_application_service=self._fingpt_application_service,
        )
        return self._research_port

    async def run_research(
        self,
        ticker: str,
        query: str,
        user_id: int,
        *,
        thread_id: str | None = None,
        llm_profile: dict[str, Any] | None = None,
    ) -> GenericResponseDTO:
        port = self._resolve_research_port()
        raw = await port.run_research(
            ticker,
            query,
            user_id,
            thread_id=thread_id,
            llm_profile=llm_profile,
        )
        return build_ai_research_response(raw)

    async def run_chat(
        self,
        message: str,
        user_id: int,
        *,
        thread_id: str | None = None,
    ) -> GenericResponseDTO:
        from .ai_chat_service import run_chat_with_tools
        tid = thread_id if thread_id else f"chat:{user_id}"
        conversation_history = self.get_chat_history(user_id, limit=20, thread_id=tid)
        self._append_chat_message(user_id, tid, "user", message)
        result = await run_chat_with_tools(message, user_id, conversation_history)
        result["thread_id"] = tid
        answer = str(result.get("agent_summary") or result.get("summary") or "")
        self._append_chat_message(user_id, tid, "assistant", answer, ok=bool(result.get("ok", True)))
        return result

    def get_chat_history(self, user_id: int, limit: int = 50, thread_id: str | None = None) -> list[dict]:
        with self._chat_history_lock:
            rows = list(self._chat_history.get(str(user_id), []))
        if thread_id:
            rows = [row for row in rows if row.get("thread_id") == thread_id]
        return rows[-max(1, int(limit or 50)):]

    def clear_chat_history(self, user_id: int, thread_id: str | None = None) -> None:
        user_key = str(user_id)
        with self._chat_history_lock:
            if not thread_id:
                self._chat_history[user_key] = []
                return
            self._chat_history[user_key] = [
                row for row in self._chat_history.get(user_key, [])
                if row.get("thread_id") != thread_id
            ]

    def _append_chat_message(
        self,
        user_id: int,
        thread_id: str,
        role: str,
        content: str,
        *,
        ok: bool = True,
    ) -> None:
        row = {
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "ok": ok,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        with self._chat_history_lock:
            bucket = self._chat_history.setdefault(str(user_id), [])
            bucket.append(row)
            if len(bucket) > 500:
                del bucket[:-500]


_default_ai_research_service: AiResearchService | None = None


def get_ai_research_service() -> AiResearchService:
    """Lazy singleton for tools/tasks (prefer ``service_bundle.ai_research_service`` in Flask)."""
    global _default_ai_research_service
    if _default_ai_research_service is None:
        _default_ai_research_service = AiResearchService()
    return _default_ai_research_service
