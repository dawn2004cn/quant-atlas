from __future__ import annotations

"""AI Investment Committee Service - Multi-agent debate engine using BaseAgentWorkflowEngine."""


from datetime import datetime

from app.core.logger import get_logger
from app.domain.dto.agent_workflow_dto import AgentConfig
from app.domain.dto.ai_dto import AgentResultDTO, DebateResponseDTO
from app.domain.enums import MarketCode

from .base_agent_workflow import BaseAgentWorkflowEngine

logger = get_logger(__name__)


class AICommitteeService:
    def __init__(self, stock_service: object, ai_adapter: object):
        self._stock_service = stock_service
        self._ai_adapter = ai_adapter
        self._workflow_engine = BaseAgentWorkflowEngine(ai_adapter=ai_adapter)
        self._agents = [
            AgentConfig(
                id="buffett",
                name="巴菲特 Agent",
                role="基本面 · 价值投资派",
                avatar="📊",
                prompt_prefix="你是一位资深的价值投资者，模仿巴菲特的风格。请重点关注财务稳健性、ROE、护城河和估值。基于以下数据给出你的观点：",
                weight=0.2,
            ),
            AgentConfig(
                id="lynch",
                name="彼得·林奇 Agent",
                role="技术面 · 成长投资派",
                avatar="📈",
                prompt_prefix="你是一位追求成长的投资者，模仿彼得·林奇。请重点关注技术指标（RSI, MA）、成交量和短期爆发力。基于以下数据给出你的观点：",
                weight=0.15,
            ),
            AgentConfig(
                id="wood",
                name="卡尔·伍德 Agent",
                role="主题投资 · 宏观派",
                avatar="🎯",
                prompt_prefix="你是一位宏观主题分析师，关注行业赛道、政策导向和未来潜力。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="ackman",
                name="比尔·阿克曼 Agent",
                role="激进投资派",
                avatar="⚔️",
                prompt_prefix="你是一位激进型投资人，模仿比尔·阿克曼。请重点关注品牌护城河、FCF、杠杆率和 activist potential。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="burry",
                name="迈克尔·伯里 Agent",
                role="深度价值 · 反转型",
                avatar="🔍",
                prompt_prefix="你是《大空头》原型，逆向思维猎手。请重点关注深度价值、隐藏资产和困境反转机会。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="druckenmiller",
                name="斯坦利·德拉肯米勒 Agent",
                role="宏观对冲 · 动量",
                avatar="🎲",
                prompt_prefix="你是一位宏观传奇，模仿斯坦利·德拉肯米勒。请重点关注高度不对称的进攻机会、宏观环境和动量因子。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="taleb",
                name="纳西姆·塔勒布 Agent",
                role="反脆弱 · 尾部风险",
                avatar="🛡️",
                prompt_prefix="你是《黑天鹅》作者，专注于尾部风险和反脆弱性。请重点关注凸性结构、极端下行保护和抗跌性。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="risk_man",
                name="风控 Agent",
                role="风险控制 · 职业量化",
                avatar="⛑️",
                prompt_prefix="你是一位冷酷的风险管理专家。请重点关注波动率、下行风险、Beta敞口和黑天鹅预警。基于以下数据给出你的观点：",
                weight=0.1,
            ),
            AgentConfig(
                id="sentiment",
                name="情绪 Agent",
                role="市场情绪 · 舆情派",
                avatar="💬",
                prompt_prefix="你是一位市场情绪分析师。请重点关注舆情热度、资金流向、社交媒体情绪和龙虎榜动向。基于以下数据给出你的观点：",
                weight=0.05,
            ),
        ]

    def run_debate(self, symbol: str, market_code: str) -> DebateResponseDTO:
        market = MarketCode(market_code.upper())
        detail = self._stock_service.get_stock_detail(symbol, market)
        profile = detail.get("profile", {}) if isinstance(detail, dict) else {}
        context_data = {
            "quote": profile.get("realtime", {}) if isinstance(profile, dict) else {},
            "indicators": detail.get("indicators", {}) if isinstance(detail, dict) else {},
            "news": (detail.get("news", []) or [])[:5] if isinstance(detail, dict) else [],
        }

        from app.domain.dto import AgentContext
        context = AgentContext(
            symbol=symbol,
            market=market.value,
            quote=context_data.get("quote", {}),
            indicators=context_data.get("indicators", {}),
            news=context_data.get("news", []),
        )

        state = self._workflow_engine.run_workflow(
            context=context,
            agent_configs=self._agents,
            max_parallel=6,
        )

        consensus = self._workflow_engine.compute_consensus(
            results=state.agent_results,
            agents=self._agents,
        )

        return DebateResponseDTO(
            symbol=symbol,
            market=market_code,
            timestamp=datetime.now().isoformat(),
            steps=[
                AgentResultDTO(
                    agent_id=r.agent_id,
                    agent_name=r.agent_name,
                    agent_role=r.agent_role,
                    agent_avatar=next((a.avatar for a in self._agents if a.id == r.agent_id), ""),
                    signal=r.signal.value,
                    reasoning=r.reasoning,
                    metrics=r.metrics,
                    timestamp=r.timestamp,
                )
                for r in state.agent_results
            ],
            consensus=consensus,
        )
