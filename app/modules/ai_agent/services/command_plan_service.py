from __future__ import annotations

"""Command-first planning for compound Jarvis instructions."""

import re
from typing import Any
from urllib.parse import urlencode

from app.core.logger import get_logger
from app.domain.intent_decomposer import ExecutionPlan

logger = get_logger(__name__)

_PATTERN_STYLE_RE = re.compile(
    r"赚钱|成功模式|去年|风格|偏好|适合我",
    re.IGNORECASE,
)


class CommandPlanService:
    """Parse a command into trigger/action steps without executing side effects."""

    def build_semantic_plan(
        self,
        command: str,
        *,
        user_id: str | int | None = None,
        knowledge: Any | None = None,
    ) -> dict[str, Any]:
        """Fuzzy intent routing with optional UserKnowledge cross-year pattern hints."""
        text = (command or "").strip()
        base = self.build_plan(text)
        intent = "direct_command"
        label = "执行复合指令计划"
        url = base.get("execution_endpoint") or "/market-panorama"

        if _PATTERN_STYLE_RE.search(text):
            intent = "pattern_stock_pick"
            label = "按历史赚钱风格筛选标的"
            params: dict[str, str] = {"jarvis": "winning_style"}
            if knowledge is not None and user_id is not None:
                try:
                    profile = knowledge.get_profile(user_id)
                    wins = [
                        p
                        for p in profile.get("decision_patterns") or []
                        if str(p.get("outcome") or "").lower()
                        in {"win", "profit", "success", "correct", "bullish", "positive"}
                    ]
                    sectors: list[str] = []
                    for pat in wins[-10:]:
                        sectors.extend(str(s) for s in (pat.get("sectors") or []) if s)
                    if sectors:
                        params["sectors"] = ",".join(sorted(set(sectors))[:3])
                        label = f"匹配成功模式 · 板块 {params['sectors']}"
                except Exception:
                    logger.warning("Suppressed exception", exc_info=True)
                    pass
            url = "/market-panorama?" + urlencode(params)
        elif "语音" in text or "播报" in text:
            intent = "voice_briefing"
            label = "叙事语音简报"
            url = "/voice-briefing"
        elif any(k in text for k in ("压力测试", "黑天鹅", "war room", "模拟战")):
            intent = "war_room"
            label = "War Room 反事实模拟"
            url = "/war-room"

        base["intent"] = intent
        base["label"] = label
        base["url"] = url
        base["user_id"] = user_id
        return base

    def decompose_to_plan(self, command: str, *, user_id: str | int | None = None, symbol: str = "") -> ExecutionPlan:
        from app.modules.ai_agent.services.intention.intent_decomposer import IntentDecomposer

        return IntentDecomposer().decompose(command, symbol=symbol)

    def build_plan(self, command: str) -> dict[str, Any]:
        text = (command or "").strip()
        symbol = self._symbol(text)
        condition_text, action_text = self._split_condition_action(text)
        return {
            "schema_version": "v1",
            "command": text,
            "symbol": symbol,
            "intent": "conditional_automation" if condition_text else "direct_command",
            "triggers": self._triggers(condition_text or text),
            "actions": self._actions(action_text or text, symbol=symbol),
            "requires_confirmation": True,
            "execution_endpoint": "/api/v1/workflows/trading" if symbol else "/api/v1/workflow-hub",
        }

    def _split_condition_action(self, text: str) -> tuple[str, str]:
        match = re.search(r"如果(.+?)(?:请|就|则)(.+)", text)
        if not match:
            return "", text
        return match.group(1).strip(), match.group(2).strip()

    def _symbol(self, text: str) -> str:
        match = re.search(r"\b(\d{6})\b", text)
        return match.group(1) if match else ""

    def _triggers(self, text: str) -> list[dict[str, Any]]:
        triggers: list[dict[str, Any]] = []
        if "20日线" in text or "20 日线" in text:
            op = "break_below" if any(word in text for word in ("跌破", "低于", "下破")) else "cross"
            triggers.append({"type": "moving_average", "window": 20, "operator": op})
        rsi_match = re.search(r"RSI\s*(?:小于|低于|<)\s*(\d+)", text, flags=re.IGNORECASE)
        if rsi_match:
            triggers.append({"type": "indicator", "name": "RSI", "operator": "<", "value": int(rsi_match.group(1))})
        price_match = re.search(r"(?:跌破|低于|小于)\s*(\d+(?:\.\d+)?)", text)
        if price_match and "RSI" not in text.upper():
            triggers.append({"type": "price", "operator": "<", "value": float(price_match.group(1))})
        return triggers

    def _actions(self, text: str, *, symbol: str) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        if "邮件" in text or "email" in text.lower():
            actions.append({"type": "notify", "channel": "email"})
        if "提醒" in text or "预警" in text:
            actions.append({"type": "alert", "symbol": symbol})
        if "分析报告" in text or "技术面" in text:
            actions.append({"type": "generate_report", "report_type": "technical", "symbol": symbol})
        if not actions:
            actions.append({"type": "navigate_or_search", "query": text})
        return actions

