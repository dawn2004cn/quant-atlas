from __future__ import annotations

"""AI 投资委员会 - Agent 服务层"""


from dataclasses import dataclass

from app.core.llm_config import get_llm
from app.core.logger import get_logger
from app.infrastructure.agent.investment_committee import (
    AIInvestmentCommittee,
    MarketIndex,
    StockSignal,
    StrategyLibrary,
)
from app.infrastructure.agent.investment_committee_db import MarketDataProvider, TradeRecorder

logger = get_logger(__name__)


@dataclass
class AgentOpinion:
    """单个 Agent 的意见"""
    agent_name: str
    opinion: str
    confidence: float
    evidence: list[str]


@dataclass
class CommitteeDecision:
    """委员会最终决策"""
    overall_regime: str
    risk_level: str
    selected_stocks: list[StockSignal]
    trade_decisions: list[dict]
    agent_opinions: list[AgentOpinion]
    reasoning: str


class CommitteeAgent:
    """投资委员会 Agent 基类"""

    def __init__(self, name: str, llm=None):
        self.name = name
        self.llm = llm or get_llm()

    def analyze(self, data: dict) -> AgentOpinion:
        """分析方法 - 子类实现"""
        raise NotImplementedError


class MacroAgent(CommitteeAgent):
    """宏观分析 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        market_data = data.get("market_analysis", {})
        regime = market_data.get("overall_regime", "未知")

        opinion = f"宏观视角：当前市场处于{regime}状态。"
        if regime == "牛市":
            opinion += " 经济复苏流动性充裕，建议积极进攻。"
        elif regime == "熊市":
            opinion += " 经济下行风险偏好下降，建议防守为主。"
        else:
            opinion += " 宏观预期不明，建议均衡配置。"

        return AgentOpinion(
            agent_name="宏观分析师",
            opinion=opinion,
            confidence=0.8,
            evidence=["GDP增速", "CPI/PPI", "社融数据", "人民币汇率"]
        )


class IndustryAgent(CommitteeAgent):
    """行业分析 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        return AgentOpinion(
            agent_name="行业分析师",
            opinion="关注科技、新能源、消费三大主线，轮动配置",
            confidence=0.75,
            evidence=["行业景气度", "政策支持", "资金流向"]
        )


class FundamentalAgent(CommitteeAgent):
    """财务分析 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        return AgentOpinion(
            agent_name="财务分析师",
            opinion="优选高ROE、低估值、高成长的优质标的",
            confidence=0.85,
            evidence=["净利润增速", "毛利率", "现金流", "商誉"]
        )


class TechnicalAgent(CommitteeAgent):
    """技术分析 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        strategies = data.get("strategies", [])
        return AgentOpinion(
            agent_name="技术分析师",
            opinion=f"推荐策略：{' / '.join(strategies[:3])}，顺应趋势操作",
            confidence=0.7,
            evidence=["均线形态", "成交量", "MACD", "KDJ"]
        )


class SentimentAgent(CommitteeAgent):
    """市场情绪 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        return AgentOpinion(
            agent_name="情绪分析师",
            opinion="市场情绪偏暖，涨停家数增加，短线活跃度提升",
            confidence=0.65,
            evidence=["涨停家数", "北向资金", "融资融券", "舆情监控"]
        )


class RiskAgent(CommitteeAgent):
    """风险管理 Agent"""

    def analyze(self, data: dict) -> AgentOpinion:
        risk = data.get("market_analysis", {}).get("risk_level", "medium")
        opinion = f"风险等级：{risk}。"
        if risk == "high":
            opinion += " 建议控制仓位在 30% 以下，设置严格止损。"
        elif risk == "low":
            opinion += " 仓位可提升至 70%，积极把握机会。"
        else:
            opinion += " 建议保持 50% 中性仓位。"

        return AgentOpinion(
            agent_name="风险管理师",
            opinion=opinion,
            confidence=0.9,
            evidence=["波动率", "最大回撤", "夏普比率", "组合风险"]
        )


class ChenXiaoQunAgent(CommitteeAgent):
    """陈小群短线选手 - 专门做短线"""

    def __init__(self, llm=None):
        super().__init__("陈小群短线选手", llm)
        self.strategy_library = StrategyLibrary()

    def analyze(self, data: dict) -> AgentOpinion:
        """短线选股逻辑"""
        market = data.get("market_analysis", {})
        regime = market.get("overall_regime", "震荡市")

        # 短线策略
        if regime == "牛市":
            strategies = ["米iller维尼 VCP", "缺口动量"]
        elif regime == "熊市":
            strategies = ["VSA 恐慌停止量", "维克多 2B"]
        else:
            strategies = ["TTM 挤压", "布林+RSI 极限反转"]

        opinion = f"短线策略池：{', '.join(strategies)}。重点关注资金流向和技术形态突破的标的。"

        return AgentOpinion(
            agent_name="陈小群短线选手",
            opinion=opinion,
            confidence=0.75,
            evidence=["换手率", "量价配合", "分时图", "龙虎榜"]
        )


class InvestmentCommitteeService:
    """AI 投资委员会服务"""

    def __init__(self):
        self.committee = AIInvestmentCommittee()
        self.recorder = TradeRecorder()
        self.market_data = MarketDataProvider()
        self.agents = self._init_agents()

    def _init_agents(self) -> dict[str, CommitteeAgent]:
        """初始化所有 Agent"""
        return {
            "macro": MacroAgent("宏观分析师"),
            "industry": IndustryAgent("行业分析师"),
            "fundamental": FundamentalAgent("财务分析师"),
            "technical": TechnicalAgent("技术分析师"),
            "sentiment": SentimentAgent("情绪分析师"),
            "risk": RiskAgent("风险管理"),
            "chenshaoqun": ChenXiaoQunAgent(),
        }

    def run_analysis(self) -> CommitteeDecision:
        """运行完整的投资委员会分析"""

        # 1. 获取市场数据
        logger.info("正在获取市场数据...")
        index_data = {}
        index_codes = {
            MarketIndex.SHANGHAI: "000001.SH",
            MarketIndex.SHENZHEN: "399001.SZ",
            MarketIndex.CHINEXT: "399006.SZ",
            MarketIndex.STAR: "000688.SH",
            MarketIndex.BEIJING: "899050.BJ",
        }

        for idx, code in index_codes.items():
            df = self.market_data.get_index_data(code, days=250)
            if df is not None and hasattr(df, 'empty') and not df.empty:
                index_data[idx] = df

        # 2. 分析市场状态
        logger.info("正在分析市场状态...")
        market_analysis = self.committee.analyze_markets(index_data)

        # 3. 各 Agent 发表意见
        logger.info("正在收集各 Agent 意见...")
        agent_opinions = []
        strategies = self.committee.strategy_library.get_strategies_for_regime(
            market_analysis.overall_regime.value
        )

        for _name, agent in self.agents.items():
            opinion = agent.analyze({
                "market_analysis": {
                    "overall_regime": market_analysis.overall_regime.value,
                    "risk_level": market_analysis.risk_level,
                },
                "strategies": strategies,
            })
            agent_opinions.append(opinion)

        # 4. 选股
        logger.info("正在选股...")
        stock_pool = self.market_data.get_stock_pool(limit=50)
        selected = self.committee.select_stocks(market_analysis, stock_pool)

        # 5. 执行交易
        logger.info("正在执行交易...")
        trade_decisions = []
        for signal in selected:
            # 检查现有持仓，不超过 5 只
            if len(self.committee.portfolio.positions) >= 5:
                break

            trade = self.committee.execute_trade(signal, "buy")
            if trade:
                trade_dict = {
                    "symbol": trade.symbol,
                    "name": trade.name,
                    "strategy": trade.strategy,
                    "direction": trade.direction,
                    "price": trade.price,
                    "quantity": trade.quantity,
                    "amount": trade.amount,
                    "trade_time": trade.trade_time,
                    "status": trade.status,
                }
                self.recorder.save_trade(trade_dict)
                trade_decisions.append(trade_dict)

        # 6. 检查持仓（止损止盈）
        logger.info("正在检查持仓...")
        closed = self.committee.check_positions()
        for record in closed:
            trade_dict = {
                "symbol": record.symbol,
                "name": record.name,
                "strategy": record.strategy,
                "direction": record.direction,
                "price": record.price,
                "quantity": record.quantity,
                "amount": record.amount,
                "trade_time": record.trade_time,
                "pnl": record.pnl,
                "pnl_pct": record.pnl_pct,
                "status": record.status,
            }
            self.recorder.save_trade(trade_dict)
            trade_decisions.append(trade_dict)

        # 7. 生成决策
        reasoning = f"综合7位分析师意见，当前市场为{market_analysis.overall_regime.value}，"
        reasoning += f"风险等级{market_analysis.risk_level}，"
        reasoning += f"推荐策略：{', '.join(market_analysis.recommended_strategies)}，"
        reasoning += f"选出{len(selected)}支标的进行操作。"

        return CommitteeDecision(
            overall_regime=market_analysis.overall_regime.value,
            risk_level=market_analysis.risk_level,
            selected_stocks=selected,
            trade_decisions=trade_decisions,
            agent_opinions=agent_opinions,
            reasoning=reasoning,
        )


def create_committee_service() -> InvestmentCommitteeService:
    """创建投资委员会服务实例"""
    return InvestmentCommitteeService()


# 导出
__all__ = [
    "CommitteeAgent",
    "MacroAgent",
    "IndustryAgent",
    "FundamentalAgent",
    "TechnicalAgent",
    "SentimentAgent",
    "RiskAgent",
    "ChenXiaoQunAgent",
    "InvestmentCommitteeService",
    "create_committee_service",
]
