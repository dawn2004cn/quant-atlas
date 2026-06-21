from __future__ import annotations
"""TradingAgents-style orchestration service (6 analysts + debates + quant_tools)."""


from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from langchain_core.language_models.chat_models import BaseChatModel

from ..core.runtime_config import get_runtime

from ..core.llm_config import get_llm

if TYPE_CHECKING:
    from ..modules.ai_agent.services.fingpt_application_service import FinGPTApplicationService
from .research import build_custom_trading_graph, package_full_report
from .research_checkpointer import CheckpointerHandle, create_checkpointer_handle_from_env

from ..core.logger import get_logger


logger = get_logger(__name__)


def _enrich_research_failure_message(exc: Exception) -> str:
    """把底层 SDK 的简短报错扩展为可操作的排查说明（不改变正常成功路径）。"""
    raw = (str(exc) or "").strip() or type(exc).__name__
    name = type(exc).__name__
    lower = raw.lower()
    bits: list[str] = []

    if "APIConnection" in name or "ConnectError" in name or "connection" in lower:
        bits.append(
            "大模型 HTTP 连接失败：本进程无法连上 OpenAI 兼容端点。"
            "若使用 Ollama，请先在本机启动 `ollama serve`，并设置环境变量 "
            "`OLLAMA_HOST=http://127.0.0.1:11434`（或 `OPENAI_BASE_URL` 指向带 `/v1` 的网关），"
            "同时设置 `TRADING_AGENTS_MODEL` 为已 `ollama pull` 的模型名。"
        )
        base = get_runtime("OPENAI_BASE_URL", "") or get_runtime("OLLAMA_HOST", "")
        bits.append(
            "当前环境：OPENAI_BASE_URL / OLLAMA_HOST = "
            + (repr(base) if base else "（均未设置，将尝试 OpenAI 官方地址，需可访问外网且配置 OPENAI_API_KEY）")
        )
    if "timeout" in lower or "timed out" in lower:
        bits.append("请求超时：可适当增大环境变量 TRADING_AGENTS_TIMEOUT_SEC，或检查模型推理是否过慢。")
    if "401" in raw or "403" in raw or "unauthorized" in lower:
        bits.append("鉴权失败：请检查 OPENAI_API_KEY 以及 base_url 是否与密钥所属平台一致。")

    if not bits:
        return raw
    return raw + "\n\n" + "\n".join(bits)


def _default_llm() -> BaseChatModel:
    """使用统一的 LLM 工厂获取模型实例。"""
    return get_llm()


def _default_llm_for_user(user_id: int, provider_service: Any) -> BaseChatModel:
    """Build LLM client using per-user config from provider_service."""
    if provider_service is None:
        return get_llm()
    try:
        config = provider_service.resolve(user_id, "default")
        return provider_service.build_client(config)
    except Exception as exc:
        logger.warning("LLMProviderService failed for user=%d, falling back to global singleton: %s",
                       user_id, exc)
        return get_llm()


class TradingAgentsService:
    """
    对外统一入口：基于 ``app.agents.research`` 的 LangGraph，
    使用 ``quant_tools`` 与平台回测/行情服务；内置 **checkpoint**（内存或 Postgres）。

    启动前请确保已调用 ``configure_quant_tools()``（通常在 ``bootstrap`` 中）。

    多轮对话：对同一 ``thread_id`` 重复调用 ``run_research`` 会在状态中累积
    ``conversation_log``（checkpoint 持久化）；``thread_id`` 默认按用户+标的生成。
    """

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        *,
        llm_provider_service: Any = None,
        checkpointer_handle: CheckpointerHandle | None = None,
        fingpt_application_service: "FinGPTApplicationService | None" = None,
    ) -> None:
        self._cp_handle = checkpointer_handle or create_checkpointer_handle_from_env()
        self._llm = llm or _default_llm()
        # Store reference for user-aware config resolution
        self._llm_provider_service = llm_provider_service
        self._graph = build_custom_trading_graph(
            self._llm,
            checkpointer=self._cp_handle.saver,
            fingpt_application_service=fingpt_application_service,
        )

    def close(self) -> None:
        """释放 Postgres checkpointer 上下文（内存实现无操作）。"""
        self._cp_handle.close()

    async def run_research(
        self,
        ticker: str,
        query: str,
        user_id: int,
        *,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """
        执行完整研究流程并返回结构化报告 + Markdown 全文。

        :param ticker: 标的（与 ``quant_tools.infer_market_and_symbol`` 兼容）
        :param query: 用户研究问题 / 约束
        :param user_id: 用于 ``get_user_watchlist`` 等工具的用户主键
        :param thread_id: LangGraph ``configurable.thread_id``；相同 id 可恢复 checkpoint 与对话时间线
        """
        if not (ticker or "").strip():
            return {"ok": False, "error": "ticker_empty", "full_report_markdown": ""}
        if user_id < 1:
            return {"ok": False, "error": "invalid_user_id", "full_report_markdown": ""}

        tid = (thread_id or "").strip() or f"ta:{user_id}:{ticker.strip()}"
        config: dict[str, Any] = {"configurable": {"thread_id": tid}}

        # Rebuild LLM with user-specific config if provider_service is available
        if self._llm_provider_service is not None:
            user_llm = _default_llm_for_user(user_id, self._llm_provider_service)
            if user_llm is not self._llm:
                self._graph = build_custom_trading_graph(
                    user_llm,
                    checkpointer=self._cp_handle.saver,
                    fingpt_application_service=fingpt_application_service,
                )

        prev_log: list[str] = []
        try:
            snap = await self._graph.aget_state(config)
            if snap is not None and getattr(snap, "values", None):
                raw = snap.values.get("conversation_log")
                if isinstance(raw, list):
                    prev_log = [str(x) for x in raw]
        except Exception as exc:  # noqa: BLE001
            logger.debug("aget_state (no prior checkpoint?): %s", exc)

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = f"[{stamp}] {query.strip()}"
        init: dict[str, Any] = {
            "ticker": ticker.strip(),
            "query": (query or "").strip() or "请基于可用数据给出投资研究摘要与主要风险。",
            "user_id": int(user_id),
            "conversation_log": prev_log + [line],
        }

        try:
            final_state = await self._graph.ainvoke(init, config)
        except Exception as exc:  # noqa: BLE001
            logger.exception("TradingAgents run_research failed")
            return {
                "ok": False,
                "error": type(exc).__name__,
                "message": _enrich_research_failure_message(exc),
                "ticker": init["ticker"],
                "query": init["query"],
                "user_id": init["user_id"],
                "thread_id": tid,
                "full_report_markdown": "",
            }

        out = package_full_report(final_state)
        out["ok"] = True
        out["thread_id"] = tid
        return out
