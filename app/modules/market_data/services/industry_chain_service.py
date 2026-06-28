from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Industry chain service for stock diagnosis."""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


class IndustryChainService:
    """Build a lightweight upstream-midstream-downstream industry map."""

    def __init__(self, *, stock_service: Any, market_service: Any | None = None) -> None:
        self._stock_service = stock_service
        self._market_service = market_service

    def build_chain(self, *, symbol: str, market: MarketCode = MarketCode.CN) -> GenericResponseDTO:
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValueError("symbol_required")
        profile = self._profile(clean_symbol, market)
        industry = str(profile.get("industry") or profile.get("sector") or "未知行业")
        name = str(profile.get("name") or clean_symbol)
        nodes = [
            {"id": "upstream", "label": "上游资源/供应", "role": "成本与供给约束"},
            {"id": "midstream", "label": f"{name}", "role": f"{industry} 核心标的/观察节点"},
            {"id": "downstream", "label": "下游需求/应用", "role": "收入弹性与景气验证"},
        ]
        return {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "symbol": clean_symbol,
            "market": market.value,
            "name": name,
            "industry": industry,
            "nodes": nodes,
            "edges": [
                {"source": "upstream", "target": "midstream", "label": "成本/产能"},
                {"source": "midstream", "target": "downstream", "label": "产品/服务"},
            ],
            "opportunities": [
                f"跟踪 {industry} 的政策、订单、价格与库存变化。",
                "若行情强于行业均值，可作为资金轮动候选继续诊股。",
            ],
            "risks": [
                "上游成本上行或供给扰动会压缩利润。",
                "下游需求不及预期会削弱估值修复持续性。",
            ],
            "mermaid": (
                "flowchart LR\n"
                f"    upstream[上游资源/供应] --> midstream[{name}]\n"
                "    midstream --> downstream[下游需求/应用]"
            ),
            "evidence": ["个股基础资料", "行业字段", "新闻与诊股报告可继续补强"],
            "confidence": 0.55 if industry != "未知行业" else 0.35,
        }

    def _profile(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        try:
            detail = self._stock_service.get_stock_detail(symbol, market)
            if hasattr(detail, "profile"):
                return dict(detail.profile or {})
            if isinstance(detail, dict):
                return dict(detail.get("profile") or detail)
        except Exception as exc:
            logger.warning("industry chain profile unavailable for %s: %s", symbol, exc)
        if self._market_service is not None:
            try:
                rows = self._market_service.list_quotes(market, [symbol])
                if rows:
                    quote = rows[0].model_dump() if hasattr(rows[0], "model_dump") else dict(rows[0])
                    return quote
            except Exception as exc:
                logger.warning("industry chain quote unavailable for %s: %s", symbol, exc)
        return {"code": symbol, "name": symbol}
