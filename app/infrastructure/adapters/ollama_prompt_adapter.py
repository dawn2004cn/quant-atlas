from __future__ import annotations

"""Local Ollama single-shot analysis (no external TradingAgents dependency)."""


import logging

import requests

from app.core.circuit_breaker import CircuitBreakerOpenError, circuit_breaker

from ...core.runtime_config import get_runtime

logger = logging.getLogger(__name__)


class OllamaPromptAdapter:
    """Builds a research prompt from context and calls Ollama `/api/generate`."""

    def __init__(self) -> None:
        self._ollama_base = get_runtime("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self._model = get_runtime("OLLAMA_MODEL", "qwen2.5:7b")
        self._prompt_version = "ollama_v1"

    def analyze(self, *, symbol: str, market: str, context: dict, **kwargs) -> dict:
        custom_prompt = kwargs.get("custom_prompt", "")
        prompt_version = kwargs.get("prompt_version") or self._prompt_version
        prompt_hash = kwargs.get("prompt_hash")
        prompt = self._build_prompt(symbol=symbol, market=market, context=context, custom_prompt=custom_prompt)
        try:
            result = self._call_ollama(prompt)
            degraded = False
        except CircuitBreakerOpenError:
            logger.warning("Ollama circuit open; returning degraded analysis for %s", symbol)
            from app.core.middleware.degraded_context import mark_system_degraded

            mark_system_degraded("ollama")
            result = "Ollama 服务暂时不可用（熔断保护），请稍后重试或使用规则引擎结果。"
            degraded = True
        except Exception as exc:
            logger.warning("Ollama analyze failed for %s: %s", symbol, exc)
            result = f"Ollama 调用失败: {exc}"
            degraded = True
        from app.modules.ai_agent.services.prompt_trace import attach_prompt_trace

        return attach_prompt_trace(
            {
                "mode": kwargs.get("mode", "ollama_prompt"),
                "symbol": symbol,
                "market": market,
                "model": self._model,
                "analysis": result,
                "degraded": degraded,
            },
            prompt_id="ollama_research",
            prompt_text=prompt,
            base_version=prompt_version,
            prompt_hash=prompt_hash,
        )

    def generate(self, *, prompt: str, prompt_version: str | None = None, prompt_hash: str | None = None) -> dict:
        """通用生成接口：用于站内对话/评论等场景。"""
        try:
            result = self._call_ollama(prompt)
            degraded = False
        except CircuitBreakerOpenError:
            from app.core.middleware.degraded_context import mark_system_degraded

            mark_system_degraded("ollama")
            result = "Ollama 服务暂时不可用（熔断保护）。"
            degraded = True
        except Exception as exc:
            logger.warning("Ollama generate failed: %s", exc)
            result = f"Ollama 调用失败: {exc}"
            degraded = True
        from app.modules.ai_agent.services.prompt_trace import attach_prompt_trace

        return attach_prompt_trace(
            {
                "model": self._model,
                "text": result,
                "degraded": degraded,
            },
            prompt_id="ollama_generate",
            prompt_text=prompt,
            base_version=prompt_version,
            prompt_hash=prompt_hash,
        )

    def _build_prompt(self, *, symbol: str, market: str, context: dict, custom_prompt: str = "") -> str:
        prefix = custom_prompt if custom_prompt else "你是量化研究员，请基于以下数据做结构化分析："
        return (
            f"{prefix}\n"
            f"标的: {symbol}\n市场: {market}\n"
            f"行情摘要: {context.get('quote', {})}\n"
            f"技术指标: {context.get('indicators', {})}\n"
            f"个股新闻: {context.get('news', [])[:5]}\n"
            f"行业新闻: {context.get('industry_news', [])[:5]}\n"
            "请输出：1) 观点 2) 风险 3) 交易计划（买入/止损/止盈） 4) 置信度。"
        )

    @circuit_breaker("ollama_generate", failure_threshold=3, timeout=60)
    def _call_ollama(self, prompt: str) -> str:
        resp = requests.post(
            f"{self._ollama_base.rstrip('/')}/api/generate",
            json={"model": self._model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        payload = resp.json()
        return str(payload.get("response", "")).strip()
