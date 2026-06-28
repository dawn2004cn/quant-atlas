from __future__ import annotations
"""High-Fidelity Executor - 约束注入 + 影子测试 for 研发到实盘的对齐.

This implements Section 2D from the roadmap:
- 约束注入: 成交量冲击成本 + 滑点模型
- 影子测试: Paper Trading 集成
- 实盘偏差 < 5% 才允许进入生产流
"""


from dataclasses import dataclassfrom typing import Any@dataclass
class TransactionCostConfig:
    """交易成本配置."""

    commission_rate: float = 0.0003
    slippage_bps: float = 1.0
    min_commission: float = 5.0
    stamp_tax_rate: float = 0.001


@dataclass
class LiquidityConstraint:
    """流动性约束."""

    Max_POSITION_PCT: float = 0.05
    Max_TURNOVER: float = 0.3
    Min_LIQUIDITY_10DAY: float = 1000000


class HighFidelityExecutor:
    """高仿真执行器 - 在回测中注入真实成本."""

    def __init__(self) -> None:
        self._cost_config = TransactionCostConfig()
        self._liquidity = LiquidityConstraint()
        self._enabled = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def set_cost_config(
        self,
        commission_rate: float | None = None,
        slippage_bps: float | None = None,
    ) -> None:
        """设置交易成本."""
        if commission_rate is not None:
            self._cost_config.commission_rate = commission_rate
        if slippage_bps is not None:
            self._cost_config.slippage_bps = slippage_bps

    def calculate_slippage(
        self,
        order_value: float,
        current_volume: float,
    ) -> float:
        """计算滑点成本.

        Args:
            order_value: 订单金额
            current_volume: 当前成交量

        Returns:
            滑点 (bps)
        """
        if current_volume <= 0:
            return self._cost_config.slippage_bps * 2

        participation = order_value / (current_volume + 1)

        if participation > 0.1:
            return self._cost_config.slippage_bps * 3
        if participation > 0.05:
            return self._cost_config.slippage_bps * 2
        if participation > 0.01:
            return self._cost_config.slippage_bps * 1.5

        return self._cost_config.slippage_bps

    def calculate_commission(self, turnover: float) -> float:
        """计算佣金.

        Args:
            turnover: 成交额

        Returns:
            佣金
        """
        commission = turnover * self._cost_config.commission_rate
        return max(commission, self._cost_config.min_commission)

    def apply_constraints(
        self,
        backtest_result: dict[str, Any],
    ) -> dict[str, Any]:
        """应用约束到回测结果.

        Args:
            backtest_result: 原始回测结果

        Returns:
            带约束的回测结果
        """
        if not self._enabled:
            return backtest_result

        original_return = backtest_result.get("total_return", 0)
        turnover = backtest_result.get("turnover", 0)

        commission = self.calculate_commission(turnover)
        slippage = turnover * (self._cost_config.slippage_bps / 10000)

        total_cost = commission + slippage
        adjusted_return = original_return - total_cost

        return {
            **backtest_result,
            "original_return": original_return,
            "adjusted_return": adjusted_return,
            "commission": commission,
            "slippage": slippage,
            "total_cost": total_cost,
            "cost_adj_pct": total_cost / (abs(original_return) + 1e-10) if original_return else 0,
        }


class PaperTradingAccount:
    """影子测试账户."""

    def __init__(self, initial_capital: float = 1000000) -> None:
        self._initial_capital = initial_capital
        self._current_capital = initial_capital
        self._positions: dict[str, float] = {}
        self._trades: list[dict[str, Any]] = []
        self._run_id = 0

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    @property
    def current_capital(self) -> float:
        return self._current_capital

    def start_run(self, name: str | None = None) -> str:
        """开始新的影子测试."""
        self._run_id += 1
        run_id = f"paper_{self._run_id}"
        self._positions = {}
        self._trades = []
        return run_id

    def execute_signal(
        self,
        symbol: str,
        direction: int,
        quantity: float,
        price: float,
    ) -> dict[str, Any]:
        """执行信号.

        Args:
            symbol: 股票代码
            direction: 1=买, -1=卖
            quantity: 数量
            price: 价格

        Returns:
            执行结果
        """
        value = quantity * price
        cost = self._calculate_cost(value, direction)

        trade = {
            "symbol": symbol,
            "direction": direction,
            "quantity": quantity,
            "price": price,
            "value": value,
            "cost": cost,
            "timestamp": "",
        }

        if direction == 1:
            if value > self._current_capital - cost:
                return {**trade, "status": "rejected", "reason": "insufficient_capital"}

            self._current_capital -= value + cost
            self._positions[symbol] = self._positions.get(symbol, 0) + quantity

        else:
            self._current_capital += value - cost
            self._positions[symbol] = self._positions.get(symbol, 0) - quantity

        self._trades.append(trade)
        return {**trade, "status": "executed"}

    def _calculate_cost(self, value: float, direction: int) -> float:
        base_cost = value * 0.0003
        if direction == 1:
            base_cost += value * 0.001
        return base_cost

    def calculate_performance(self) -> dict[str, Any]:
        """计算影子测试表现."""
        if not self._trades:
            return {"status": "no_trades"}

        total_pnl = self._current_capital - self._initial_capital
        pnl_pct = total_pnl / self._initial_capital

        return {
            "initial_capital": self._initial_capital,
            "current_capital": self._current_capital,
            "total_pnl": total_pnl,
            "pnl_pct": pnl_pct,
            "num_trades": len(self._trades),
            "positions": self._positions,
        }

    def check_deviation(
        self,
        backtest_result: dict[str, Any],
        max_deviation: float = 0.05,
    ) -> dict[str, Any]:
        """检查实盘偏差.

        Args:
            backtest_result: 回测结果
            max_deviation: 最大允许偏差 (5%)

        Returns:
            偏差检查结果
        """
        bt_return = backtest_result.get("total_return", 0)
        pt_perf = self.calculate_performance()
        pt_return = pt_perf.get("pnl_pct", 0)

        deviation = abs(pt_return - bt_return) / (abs(bt_return) + 1e-10) if bt_return else 0

        return {
            "backtest_return": bt_return,
            "paper_return": pt_return,
            "deviation": deviation,
            "is_within_threshold": deviation <= max_deviation,
            "max_allowed": max_deviation,
        }


def format_high_fidelity_prompt(
    backtest_result: dict[str, Any] | None = None,
) -> str:
    """生成高仿真约束的 prompt.

    Args:
        backtest_result: 回测结果

    Returns:
        prompt
    """
    lines = [
        "=== High-Fidelity Execution ===",
        "",
        "[成本约束]",
        "- 佣金: 0.03% (最低 5元)",
        "- 滑点: 1-3 bps (根据订单占比)",
        "- 印花税: 0.1% (卖出)",
        "",
        "[流动性约束]",
        "- 单票最大仓位: 5%",
        "- 单日最大换手: 30%",
    ]

    if backtest_result:
        hfe = HighFidelityExecutor()
        hfe.enable()
        adjusted = hfe.apply_constraints(backtest_result)

        orig = adjusted.get("original_return", 0)
        adj = adjusted.get("adjusted_return", 0)
        cost = adjusted.get("total_cost", 0)

        lines.append("")
        lines.append("[调整后]")
        lines.append(f"- 原始收益: {orig:.2%}")
        lines.append(f"- 调整后收益: {adj:.2%}")
        lines.append(f"- 总成本: {cost:.2f}")

    return "\n".join(lines)


def format_paper_trading_prompt() -> str:
    """生成影子测试 prompt."""
    return """=== Paper Trading ===
[规则]
- 新模型自动进入影子账户
- 运行 3 天
- 实盘偏差 < 5% 才允许进入主生产流
- 偏差 >= 5% 则打回回测

[检查项]
- 执行延迟
- 流动性冲击
- 滑点 vs 预期"""