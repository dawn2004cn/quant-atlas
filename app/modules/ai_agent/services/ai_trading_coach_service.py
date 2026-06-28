from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""AI Post-Trade Coach - AI交易教练服务.

分析用户操作记录，指出逻辑缺陷，培养有纪律的交易习惯。"""


from collections import defaultdict
from datetime import datetime



class TradingPatternAnalyzer:
    """交易模式分析器."""

    @staticmethod
    def analyze_mistakes(
        operation_history: list[dict],
    ) -> GenericResponseDTO:
        """分析错误模式."""
        # 按RSI区间分类
        rsi_buy_pattern = defaultdict(list)
        rsi_sell_pattern = defaultdict(list)

        for op in operation_history:
            rsi_zone = op.get("rsi_zone", "unknown")
            action = op.get("action", "")

            if action == "buy":
                rsi_buy_pattern[rsi_zone].append(op)
            elif action == "sell":
                rsi_sell_pattern[rsi_zone].append(op)

        # 检测RSI超买区追涨
        overbought_buys = len(rsi_buy_pattern.get("overbought", []))
        oversold_sells = len(rsi_sell_pattern.get("oversold", []))

        mistakes = []

        if overbought_buys >= 2:
            mistakes.append({
                "pattern": "overbought_buy",
                "description": f"近{overbought_buys}次亏损都是在RSI>80超买区追涨",
                "frequency": overbought_buys,
                "suggestion": "建议在RSI>70时停止买入，等待回调",
            })

        if oversold_sells >= 2:
            mistakes.append({
                "pattern": "panic_sell",
                "description": f"近{oversold_sells}次亏损都是在RSI<20超卖区恐慌抛售",
                "frequency": oversold_sells,
                "suggestion": "建议设置固定止损位，不要手动平仓",
            })

        return {
            "mistakes": mistakes,
            "pattern_summary": dict(rsi_buy_pattern),
        }


class AITradingCoachService:
    """AI交易教练服务."""

    def analyze_trading_history(
        self,
        user_id: int,
        operations: list[dict],
    ) -> GenericResponseDTO:
        """分析用户的交易历史并给出改进建议."""
        if not operations:
            return {
                "ok": True,
                "message": "暂无交易记录",
                "suggestions": ["开始记录您的交易，不断复盘改进"],
            }

        # 统计胜率
        wins = sum(1 for op in operations if op.get("pnl", 0) > 0)
        total = len(operations)
        win_rate = wins / total if total > 0 else 0

        # 分析错误模式
        pattern_analysis = TradingPatternAnalyzer.analyze_mistakes(operations)

        # 计算平均持仓时间
        hold_times = []
        for op in operations:
            if op.get("action") == "sell" and op.get("hold_days"):
                hold_times.append(op["hold_days"])

        avg_hold_days = sum(hold_times) / len(hold_times) if hold_times else 0

        return {
            "ok": True,
            "user_id": user_id,
            "generated_at": datetime.now().isoformat(),
            "statistics": {
                "total_trades": total,
                "wins": wins,
                "losses": total - wins,
                "win_rate": round(win_rate * 100, 1),
                "avg_hold_days": round(avg_hold_days, 1),
            },
            "mistakes": pattern_analysis.get("mistakes", []),
            "coach_feedback": self._generate_coach_feedback(
                win_rate, pattern_analysis
            ),
        }

    def _generate_coach_feedback(
        self,
        win_rate: float,
        pattern_analysis: dict,
    ) -> str:
        """生成教练反馈."""
        mistakes = pattern_analysis.get("mistakes", [])

        if win_rate < 0.4:
            feedback = "您的胜率偏低，建议先减少交易频率，提高选股标准。"
        elif win_rate < 0.5:
            feedback = "胜率一般，建议优化入场时机。"
        else:
            feedback = "保持良好的交易习惯，继续复盘改进。"

        if mistakes:
            feedback += f" 另外注意：{mistakes[0].get('suggestion', '')}"

        return feedback


class DisciplineAuditorService:
    """纪律审计服务."""

    @staticmethod
    def audit_discipline(
        operations: list[dict],
        stop_loss_rules: dict | None = None,
    ) -> GenericResponseDTO:
        """审计是否遵守交易纪律."""
        violations = []

        for op in operations:
            if op.get("action") != "sell":
                continue

            # 检测是否按计划止损
            if stop_loss_rules:
                planned_stop = op.get("planned_stop_loss")
                actual_price = op.get("sell_price")

                if planned_stop and actual_price:
                    if actual_price < planned_stop * 0.95:
                        violations.append({
                            "type": "stop_loss_violation",
                            "symbol": op.get("symbol"),
                            "description": f"未按计划止损，实际卖出低于计划{((planned_stop - actual_price) / planned_stop * 100):.1f}%",
                        })

        if violations:
            return {
                "status": "violations",
                "violations": violations,
                "message": f"发现{len(violations)}次违规，建议写下违规原因以加深印象",
            }

        return {
            "status": "compliant",
            "message": "交易纪律执行良好",
        }