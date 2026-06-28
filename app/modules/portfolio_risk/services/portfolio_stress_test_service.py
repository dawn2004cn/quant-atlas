from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Portfolio Stress Test - 组合压力测试服务."""


from datetime import datetime

from app.core.base_service import BaseApplicationService
from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider


class StressTestScenarios:
    """压力测试场景定义."""

    SCENARIOS = {
        "market_crash_3": {
            "name": "大盘下跌3%",
            "index_change": -3,
            "description": "模拟大盘系统性下跌",
        },
        "market_crash_5": {
            "name": "大盘下跌5%",
            "index_change": -5,
            "description": "模拟市场恐慌性下跌",
        },
        "sector_crash_10": {
            "name": "板块下跌10%",
            "sector_change": -10,
            "description": "模拟持仓板块整体回调",
        },
        "stock_crash_20": {
            "name": "个股跌停",
            "stock_change": -20,
            "description": "模拟持仓个股突发跌停",
        },
        "market_rally": {
            "name": "大盘上涨3%",
            "index_change": 3,
            "description": "模拟市场反弹",
        },
    }


class PortfolioStressTestService(BaseApplicationService):
    """组合压力测试服务."""

    def __init__(
        self,
        market_provider: MarketDataProvider | None = None,
    ):
        super().__init__()
        self._market = market_provider
        self._scenarios = StressTestScenarios()

    def run_stress_test(
        self,
        symbols: list[str],
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """运行压力测试."""
        # 获取持仓信息
        holdings = []
        total_value = 0

        for symbol in symbols:
            profile = self._market.get_stock_profile(symbol, market) if self._market else {}
            if not profile:
                continue

            price = float(profile.get("price", 0) or 0)
            if price <= 0:
                continue

            change_pct = float(profile.get("change_pct", 0) or 0)
            holdings.append({
                "symbol": symbol,
                "name": profile.get("name", symbol),
                "price": price,
                "change_pct": change_pct,
                "value": price * 100,  # 假设100股
            })
            total_value += price * 100

        if not holdings:
            return {"ok": False, "error": "无持仓数据"}

        # 计算各场景影响
        scenarios_results = []
        all_scenarios = self._scenarios.SCENARIOS

        for key, scenario in all_scenarios.items():
            result = self._calculate_scenario_impact(
                holdings=holdings,
                total_value=total_value,
                scenario=scenario,
            )
            scenarios_results.append(result)

        # 排序找出最坏情况
        worst_case = min(scenarios_results, key=lambda x: x["portfolio_value_change"])

        # 计算相关性风险
        correlation_risk = self._check_portfolio_correlation(symbols)

        return {
            "ok": True,
            "generated_at": datetime.now().isoformat(),
            "holdings": holdings,
            "total_value": round(total_value, 2),
            "scenarios": scenarios_results,
            "worst_case": worst_case,
            "correlation_risk": correlation_risk,
            "recommendations": self._generate_recommendations(worst_case, correlation_risk),
        }

    def _calculate_scenario_impact(
        self,
        holdings: list[dict],
        total_value: float,
        scenario: dict,
    ) -> GenericResponseDTO:
        """计算单个场景的影响."""
        index_change = scenario.get("index_change", 0)

        impacted_holdings = []
        portfolio_change = 0

        for h in holdings:
            if index_change != 0:
                # 简化：假设个股与指数高度相关
                stock_change = index_change * 1.2
            else:
                stock_change = scenario.get("stock_change", 0)

            original_value = h.get("value", 0)
            new_value = original_value * (1 + stock_change / 100)
            change = new_value - original_value

            impacted_holdings.append({
                "symbol": h["symbol"],
                "original_value": round(original_value, 2),
                "stressed_value": round(new_value, 2),
                "loss": round(change, 2),
            })

            portfolio_change += change

        portfolio_change_pct = (portfolio_change / total_value * 100) if total_value > 0 else 0

        return {
            "scenario": scenario.get("name"),
            "description": scenario.get("description"),
            "portfolio_value": round(total_value + portfolio_change, 2),
            "portfolio_value_change": round(portfolio_change, 2),
            "portfolio_change_pct": round(portfolio_change_pct, 2),
            "holdings": impacted_holdings,
        }

    def _check_portfolio_correlation(self, symbols: list[str]) -> GenericResponseDTO:
        """检查组合相关性风险."""
        # 简化实现：检查是否是同一行业
        industries = set()

        for symbol in symbols:
            profile = self._market.get_stock_profile(symbol, MarketCode.CN) if self._market else {}
            if profile:
                ind = profile.get("industry")
                if ind:
                    industries.add(ind)

        if len(industries) == 1:
            return {
                "risk": "high",
                "message": f"您的组合仅覆盖{len(industries)}个行业，风险集中",
                "suggestion": "建议分散到多个行业以降低风险",
            }
        elif len(industries) <= 2:
            return {
                "risk": "medium",
                "message": f"组合集中于{len(industries)}个行业",
                "suggestion": "可适当分散行业配置",
            }
        else:
            return {
                "risk": "low",
                "message": f"组合覆盖{len(industries)}个行业，分散度较好",
                "suggestion": "继续保持行业分散",
            }

    def _generate_recommendations(
        self,
        worst_case: dict,
        correlation_risk: dict,
    ) -> list[str]:
        """生成建议."""
        recommendations = []

        # 基于最坏情况
        if worst_case.get("portfolio_change_pct", 0) < -10:
            recommendations.append("您的组合在极端情况下可能损失超过10%，建议降低仓位")

        # 基于相关性
        if correlation_risk.get("risk") == "high":
            recommendations.append("行业过于集中，建议增加避险品种如红利股")

        if not recommendations:
            recommendations.append("当前组合风险可控，建议继续持有")

        return recommendations
