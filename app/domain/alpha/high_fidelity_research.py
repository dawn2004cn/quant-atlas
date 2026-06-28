from __future__ import annotations
"""High-Fidelity Research Loop - 高保真研发闭环.

将 DigitalTwin 的真实交易成本反馈给 RD-Agent，
实现"回测林志玲，实盘罗玉凤"的难题。
"""


from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class CostSource(Enum):
    """成本来源."""

    COMMISSION = "commission"
    SLIPPAGE = "slippage"
    MARKET_IMPACT = "market_impact"
    DELAY = "delay"
    DATA_LATENCY = "data_latency"
    API_RATE_LIMIT = "api_rate_limit"


@dataclass
class ExecutionCost:
    """执行成本明细."""

    commission: float = 0.0
    slippage: float = 0.0
    market_impact: float = 0.0
    delay_cost: float = 0.0
    data_latency_cost: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.commission
            + self.slippage
            + self.market_impact
            + self.delay_cost
            + self.data_latency_cost
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "commission": self.commission,
            "slippage": self.slippage,
            "market_impact": self.market_impact,
            "delay_cost": self.delay_cost,
            "data_latency_cost": self.data_latency_cost,
            "total": self.total,
        }


@dataclass
class FidelityAnalysis:
    """保真度分析."""

    backtest_return: float
    live_return: float
    deviation: float
    costs: ExecutionCost
    drift_reason: str | None = None
    recommendations: list[str] = field(default_factory=list)


class HighFidelityResearchLoop:
    """高保真研发闭环."""

    def __init__(self) -> None:
        self._cost_config = {
            "commission_rate": 0.0003,
            "min_commission": 5.0,
            "slippage_bps": 2.0,
            "market_impact_factor": 0.1,
            "delay_seconds": 1.0,
            "data_delay_seconds": 5.0,
        }
        self._history: list[dict[str, Any]] = []

    def set_cost_config(self, config: dict[str, Any]) -> None:
        """设置成本配置."""
        self._cost_config.update(config)

    def calculate_execution_cost(
        self,
        order_value: float,
        volume: float,
        current_volume: float,
        delay_seconds: float | None = None,
    ) -> ExecutionCost:
        """计算执行成本。

        Args:
            order_value: 订单金额
            volume: 成交量
            current_volume: 当前成交量
            delay_seconds: 延迟秒数

        Returns:
            执行成本
        """
        cfg = self._cost_config

        commission = max(order_value * cfg["commission_rate"], cfg["min_commission"])

        participation = order_value / (current_volume + 1)
        if participation > 0.1:
            slippage_bps = cfg["slippage_bps"] * 3
        elif participation > 0.05:
            slippage_bps = cfg["slippage_bps"] * 2
        else:
            slippage_bps = cfg["slippage_bps"]
        slippage = order_value * (slippage_bps / 10000)

        market_impact = (
            order_value * participation * cfg["market_impact_factor"]
        )

        delay = delay_seconds or cfg["delay_seconds"]
        delay_cost = order_value * (delay / 3600) * 0.0001

        return ExecutionCost(
            commission=commission,
            slippage=slippage,
            market_impact=market_impact,
            delay_cost=delay_cost,
        )

    def analyze_deviation(
        self,
        backtest_result: dict[str, Any],
        live_result: dict[str, Any],
    ) -> FidelityAnalysis:
        """分析回测与实盘偏差。

        Args:
            backtest_result: 回测结果
            live_result: 实盘结果

        Returns:
            偏差分析
        """
        bt_return = backtest_result.get("total_return", 0)
        live_return = live_result.get("total_return", 0)

        if bt_return == 0:
            deviation = 0.0

        else:
            deviation = abs(live_return - bt_return) / abs(bt_return)

        costs = self.calculate_execution_cost(
            order_value=backtest_result.get("turnover", 0),
            volume=backtest_result.get("volume", 0),
            current_volume=backtest_result.get("avg_volume", 0),
        )

        recommendations = []

        if costs.slippage > costs.commission * 2:
            recommendations.append("降低订单规模以减少滑点")

        if costs.market_impact > 0.01:
            recommendations.append("分批建仓以减少市场冲击")

        if costs.delay_cost > 0.001:
            recommendations.append("优化执行延迟")

        if deviation > 0.2:
            recommendations.append("高偏差：需重新回测验证策略")

        analysis = FidelityAnalysis(
            backtest_return=bt_return,
            live_return=live_return,
            deviation=deviation,
            costs=costs,
            drift_reason="cost_drift" if costs.total > 0.01 else "model_drift" if deviation > 0.1 else None,
            recommendations=recommendations,
        )

        self._history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": analysis.__dict__,
        })

        return analysis

    def generate_cost_adjusted_backtest(
        self,
        base_backtest: dict[str, Any],
    ) -> dict[str, Any]:
        """生成考虑成本后的回测结果。

        Args:
            base_backtest: 基础回测结果

        Returns:
            调整后的回测结果
        """
        turnover = base_backtest.get("turnover", 0)
        volume = base_backtest.get("volume", 0)
        avg_volume = base_backtest.get("avg_volume", 0)

        costs = self.calculate_execution_cost(
            order_value=turnover,
            volume=volume,
            current_volume=avg_volume,
        )

        adjusted_return = base_backtest.get("total_return", 0) - costs.total

        return {
            **base_backtest,
            "original_return": base_backtest.get("total_return", 0),
            "adjusted_return": adjusted_return,
            "cost_breakdown": costs.to_dict(),
            "cost_adjusted": True,
        }

    def get_history(self) -> list[dict[str, Any]]:
        """获取分析历史."""
        return self._history

    def format_fidelity_report(self) -> str:
        """生成保真度报告."""
        lines = [
            "=== High-Fidelity Research Loop ===",
            "",
            "[成本配置]",
        ]

        for k, v in self._cost_config.items():
            lines.append(f"- {k}: {v}")

        if self._history:
            latest = self._history[-1]
            analysis = latest["analysis"]
            costs = analysis["costs"]
            lines.append("")
            lines.append("[最新分析]")
            lines.append(f"  回测收益: {analysis['backtest_return']:.2%}")
            lines.append(f"  实盘收益: {analysis['live_return']:.2%}")
            lines.append(f"  偏差: {analysis['deviation']:.2%}")
            lines.append(f"  总成本: {costs['total']:.4f}")

        return "\n".join(lines)


class ProductionResearchBridge:
    """生产-研发桥接器.

    将实盘数据实时反馈给 RD-Agent 进行研发优化。
    """

    def __init__(self) -> None:
        self._loop = HighFidelityResearchLoop()
        self._feedback_queue: list[dict[str, Any]] = []

    @property
    def loop(self) -> HighFidelityResearchLoop:
        return self._loop

    def record_live_performance(
        self,
        model_id: str,
        live_metrics: dict[str, Any],
    ) -> None:
        """记录实盘表现。

        Args:
            model_id: 模型 ID
            live_metrics: 实盘指标
        """
        self._feedback_queue.append({
            "model_id": model_id,
            "metrics": live_metrics,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_research_feedback(
        self,
        model_id: str,
    ) -> dict[str, Any]:
        """获取研发反馈。

        Args:
            model_id: 模型 ID

        Returns:
            反馈信息
        """
        feedbacks = [
            f for f in self._feedback_queue
            if f["model_id"] == model_id
        ]

        if not feedbacks:
            return {"status": "no_feedback"}

        latest = feedbacks[-1]
        return {
            "status": "has_feedback",
            "recent_metrics": latest["metrics"],
            "feedback_count": len(feedbacks),
        }

    def generate_production_prompt(
        self,
        model_id: str,
    ) -> str:
        """生成包含生产反馈的 prompt。

        Args:
            model_id: 模型 ID

        Returns:
            增强的 prompt
        """
        feedback = self.get_research_feedback(model_id)

        lines = [
            "=== Production Feedback ===",
        ]

        if feedback.get("status") == "has_feedback":
            metrics = feedback["recent_metrics"]
            lines.append(f"实盘收益: {metrics.get('return', 0):.2%}")
            lines.append(f"最大回撤: {metrics.get('drawdown', 0):.2%}")
            lines.append("")
            lines.append("[建议] 基于实盘表现调整研发方向")
        else:
            lines.append("暂无实盘数据")

        return "\n".join(lines)


def format_zero_gap_research_prompt(
    fidelity_analysis: FidelityAnalysis | None = None,
) -> str:
    """生成零差距研发 prompt."""
    lines = [
        "=== Zero-Gap Research / 零差距研发 ===",
        "",
        "[目标]",
        "消除回测与实盘的差距",
        "",
        "[成本约束]",
        "- 佣金: 0.03% (最低 5元)",
        "- 滑点: 2-6 bps (根据订单规模)",
        "- 市场冲击: 0.1% * 订单占比",
        "- 执行延迟: 1秒",
        "- 数据延迟: 5秒",
    ]

    if fidelity_analysis:
        lines.extend([
            "",
            "[分析结果]",
            f"回测收益: {fidelity_analysis.backtest_return:.2%}",
            f"实盘收益: {fidelity_analysis.live_return:.2%}",
            f"偏差: {fidelity_analysis.deviation:.2%}",
            f"总成本: {fidelity_analysis.costs.total:.4f}",
        ])

        if fidelity_analysis.recommendations:
            lines.append("")
            lines.append("[优化建议]")
            for rec in fidelity_analysis.recommendations:
                lines.append(f"- {rec}")

    return "\n".join(lines)


_global_bridge: ProductionResearchBridge | None = None


def get_production_research_bridge() -> ProductionResearchBridge:
    """获取全局生产-研发桥接器."""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = ProductionResearchBridge()
    return _global_bridge