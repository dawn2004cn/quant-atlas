from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Quant Jarvis - Smart Command Service for Atlas."""

import re


class CommandService:
    def __init__(self, ai_adapter: object):
        self._ai = ai_adapter

    def parse_intent(self, query: str) -> GenericResponseDTO:
        """将用户自然语言解析为系统动作."""
        q = query.strip()

        # 1. 基础正则匹配 (极速响应)
        # 个股分析: "分析 600519" 或 "NVDA"
        code_match = re.search(r'([A-Z0-9\.-]{3,})', q.upper())
        if code_match and len(q) < 15:
            symbol = code_match.group(1)
            # 简单启发式识别市场
            market = "CN"
            if ".HK" in symbol: market = "HK"
            elif any(c.isalpha() for c in symbol) and "-" not in symbol: market = "US"
            elif "-USD" in symbol: market = "CRYPTO"

            if "分析" in q or "辩论" in q or "委员会" in q:
                return {"action": "navigate", "url": f"/ai-committee?symbol={symbol}&market={market}", "label": f"开启 {symbol} AI 投委会辩论"}
            return {"action": "navigate", "url": f"/stock/{symbol}?m={market}", "label": f"查看 {symbol} 个股详情"}

        # 2. 复杂意图通过 LLM 解析 (意图识别)
        # 这里可以调用 ollama_prompt_adapter
        # 暂时返回默认值
        if "回测" in q:
            return {"action": "navigate", "url": "/backtest", "label": "前往策略回测实验室"}
        if "自选" in q:
            return {"action": "navigate", "url": "/self-stocks", "label": "管理我的自选股列表"}
        if "因子" in q or "工厂" in q:
            return {"action": "navigate", "url": "/alpha-factory", "label": "进入 Alpha 因子工厂"}

        return {"action": "search", "url": f"/market-panorama?filter={query}", "label": f"在市场中搜索 '{query}'"}
