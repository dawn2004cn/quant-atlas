from __future__ import annotations
"""Paper Trading Integration - 影子测试完整实现.

实现 Section 2D: 影子测试集成，新模型自动进入影子账户，三天验证后偏差<5%才允许进入生产。
"""


from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class PaperTradingStatus(Enum):
    """影子测试状态."""

    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    PROMOTED = "promoted"


@dataclass
class PaperTrade:
    """单笔交易."""

    symbol: str
    direction: int
    quantity: float
    price: float
    timestamp: str
    commission: float = 0.0


@dataclass
class PaperPosition:
    """影子持仓."""

    symbol: str
    quantity: float
    avg_price: float
    current_pnl: float = 0.0


class PaperTradingAccount:
    """影子测试账户 - 完整实现."""

    def __init__(
        self,
        initial_capital: float = 1000000,
        max_deviation: float = 0.05,
    ) -> None:
        self._initial_capital = initial_capital
        self._cash = initial_capital
        self._positions: dict[str, PaperPosition] = {}
        self._trades: list[PaperTrade] = []
        self._run_id = 0
        self._status = PaperTradingStatus.PENDING
        self._max_deviation = max_deviation
        self._start_time: str | None = None
        self._backtest_result: dict[str, Any] | None = None

    @property
    def status(self) -> PaperTradingStatus:
        return self._status

    @property
    def initial_capital(self) -> float:
        return self._initial_capital

    @property
    def current_capital(self) -> float:
        return self._cash

    def start_paper(
        self,
        run_id: str,
        backtest_result: dict[str, Any] | None = None,
    ) -> None:
        """开始影子测试."""
        self._run_id += 1
        self._status = PaperTradingStatus.RUNNING
        self._start_time = datetime.utcnow().isoformat()
        self._backtest_result = backtest_result
        self._positions = {}
        self._trades = []

    def execute_order(
        self,
        symbol: str,
        direction: int,
        quantity: float,
        price: float,
    ) -> dict[str, Any]:
        """执行订单.

        Args:
            symbol: 股票代码
            direction: 1=买, -1=卖
            quantity: 数量
            price: 价格

        Returns:
            执行结果
        """
        value = quantity * price

        commission = max(value * 0.0003, 5)
        if direction == 1:
            commission += value * 0.001

        total_cost = value + commission

        trade = PaperTrade(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            price=price,
            timestamp=datetime.utcnow().isoformat(),
            commission=commission,
        )

        if direction == 1:
            if value > self._cash - commission:
                return {
                    "status": "rejected",
                    "reason": "insufficient_capital",
                    "trade": trade,
                }

            self._cash -= total_cost

            if symbol in self._positions:
                pos = self._positions[symbol]
                total_q = pos.quantity + quantity
                pos.avg_price = (
                    pos.avg_price * pos.quantity + price * quantity
                ) / total_q
                pos.quantity = total_q
            else:
                self._positions[symbol] = PaperPosition(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=price,
                )

        else:
            self._cash += value - commission

            if symbol in self._positions:
                self._positions[symbol].quantity -= quantity
                if self._positions[symbol].quantity <= 0:
                    del self._positions[symbol]

        self._trades.append(trade)
        return {"status": "executed", "trade": trade}

    def update_market_value(
        self,
        symbol: str,
        current_price: float,
    ) -> None:
        """更新市值."""
        if symbol in self._positions:
            pos = self._positions[symbol]
            pos.current_pnl = (current_price - pos.avg_price) * pos.quantity

    def calculate_performance(self) -> dict[str, Any]:
        """计算影子测试表现."""
        total_market_value = sum(
            pos.current_pnl for pos in self._positions.values()
        )

        total_value = self._cash + total_market_value
        pnl = total_value - self._initial_capital
        pnl_pct = pnl / self._initial_capital

        return {
            "initial_capital": self._initial_capital,
            "current_capital": self._cash,
            "total_value": total_value,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "num_trades": len(self._trades),
            "num_positions": len(self._positions),
            "positions": {
                s: {"quantity": p.quantity, "pnl": p.current_pnl}
                for s, p in self._positions.items()
            },
        }

    def check_deviation(self) -> dict[str, Any]:
        """检查与回测的偏差."""
        if not self._backtest_result:
            return {"error": "No backtest result to compare"}

        perf = self.calculate_performance()
        bt_return = self._backtest_result.get("total_return", 0)
        pt_return = perf["pnl_pct"]

        if bt_return == 0:
            return {"error": "Invalid backtest return"}

        deviation = abs(pt_return - bt_return) / abs(bt_return)

        passed = deviation <= self._max_deviation

        return {
            "backtest_return": bt_return,
            "paper_return": pt_return,
            "deviation": deviation,
            "max_allowed": self._max_deviation,
            "passed": passed,
            "status": "passed" if passed else "failed",
        }

    def complete(self, passed: bool) -> None:
        """完成影子测试."""
        self._status = (
            PaperTradingStatus.PASSED if passed else PaperTradingStatus.FAILED
        )


class PaperTradingScheduler:
    """影子测试调度器 - 管理多个影子测试任务."""

    def __init__(self) -> None:
        self._accounts: dict[str, PaperTradingAccount] = {}
        self._queue: list[dict[str, Any]] = []

    def create_account(
        self,
        model_id: str,
        initial_capital: float = 1000000,
    ) -> PaperTradingAccount:
        """创建影子账户."""
        account = PaperTradingAccount(initial_capital=initial_capital)
        self._accounts[model_id] = account
        return account

    def get_account(self, model_id: str) -> PaperTradingAccount | None:
        """获取影子账户."""
        return self._accounts.get(model_id)

    def submit_for_paper_trading(
        self,
        model_id: str,
        backtest_result: dict[str, Any],
    ) -> str:
        """提交模型到影子测试."""
        account = self._accounts.get(model_id)
        if not account:
            account = self.create_account(model_id)

        run_id = f"paper_{model_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        account.start_paper(run_id, backtest_result)

        self._queue.append({
            "model_id": model_id,
            "run_id": run_id,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "queued",
        })

        return run_id

    def get_queue_status(self) -> list[dict[str, Any]]:
        """获取队列状态."""
        return self._queue

    def check_all_deviations(self) -> list[dict[str, Any]]:
        """检查所有偏差."""
        results = []

        for model_id, account in self._accounts.items():
            deviation = account.check_deviation()
            results.append({
                "model_id": model_id,
                **deviation,
            })

        return results


def format_paper_trading_prompt() -> str:
    """生成影子测试 prompt."""
    return """=== Paper Trading / 影子测试 ===
[规则]
- 新模型自动进入影子账户
- 运行 3 天
- 实盘偏差 < 5% 才允许进入主生产流
- 偏差 >= 5% 则打回回测

[检查项]
- 执行延迟 (滑点)
- 流动性冲击
- 实际 vs 预期收益偏差

[成本约束]
- 佣金: 0.03% (最低 5元)
- 滑点: 1-3 bps
- 印花税: 0.1% (卖出)"""


_global_scheduler: PaperTradingScheduler | None = None


def get_paper_trading_scheduler() -> PaperTradingScheduler:
    """获取全局影子测试调度器."""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = PaperTradingScheduler()
    return _global_scheduler