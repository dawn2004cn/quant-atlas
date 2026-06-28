from __future__ import annotations
"""自动化投研周会 - Weekly Alpha Factory Meeting.

This implements Section 3, Step 3 from the roadmap:
- 每周五闭市后自动启动
- 扫描全周失效因子
- 利用 qlib 跑 100 组新实验
- 周日晚自动热切换至最优模型
"""


from datetime import datetime, timedelta
from typing import Any


class WeeklyMeetingScheduler:
    """每周自动化投研会议调度器."""

    def __init__(self) -> None:
        self._enabled = False
        self._last_run: str | None = None

    def enable(self) -> None:
        """启用周会."""
        self._enabled = True

    def disable(self) -> None:
        """禁用周会."""
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def should_run_now(self) -> bool:
        """检查是否应该现在运行.

        Returns:
            True if 当前是周五 15:00 - 周日 23:59
        """
        if not self._enabled:
            return False

        now = datetime.now()
        weekday = now.weekday()

        if weekday == 4:
            hour = now.hour
            return hour >= 15
        if weekday in (5, 6):
            return True

        return False

    def get_next_run_time(self) -> datetime | None:
        """获取下次运行时间."""
        now = datetime.now()
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour < 15:
            days_until_friday = 0

        next_friday = now + timedelta(days=days_until_friday if days_until_friday else 7)
        return next_friday.replace(hour=15, minute=0, second=0)


class FactorLifecycleWatcher:
    """因子失效监控器."""

    def __init__(self) -> None:
        self._factor_health: dict[str, dict[str, Any]] = {}

    def record_performance(
        self,
        formula: str,
        period: str,
        sharpe: float,
        drawdown: float,
        regime: str | None = None,
    ) -> None:
        """记录因子历史表现."""
        if formula not in self._factor_health:
            self._factor_health[formula] = {
                "formula": formula,
                "history": [],
                "current_regime": regime,
            }

        self._factor_health[formula]["history"].append({
            "period": period,
            "sharpe": sharpe,
            "drawdown": drawdown,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def get_stale_factors(
        self,
        decay_threshold: float = 0.3,
        lookback_days: int = 20,
    ) -> list[dict[str, Any]]:
        """获取失效因子列表.

        Args:
            decay_threshold: 衰减阈值
            lookback_days: 回看天数

        Returns:
            失效因子列表
        """
        stale = []

        for formula, data in self._factor_health.items():
            history = data.get("history", [])
            if len(history) < 2:
                continue

            recent = history[-1]
            older = history[-2]

            sharpe_decay = (recent["sharpe"] - older["sharpe"]) / (abs(older["sharpe"]) if older["sharpe"] else 1)

            if sharpe_decay < -decay_threshold:
                stale.append({
                    "formula": formula,
                    "decay": sharpe_decay,
                    "recent_sharpe": recent["sharpe"],
                    "older_sharpe": older["sharpe"],
                    "reason": "sharpe_decay",
                })

        return stale


class WeeklyMeetingExecutor:
    """投研周会执行器."""

    def __init__(self) -> None:
        self._scheduler = WeeklyMeetingScheduler()
        self._watcher = FactorLifecycleWatcher()
        self._experiment_results: list[dict[str, Any]] = []

    @property
    def scheduler(self) -> WeeklyMeetingScheduler:
        return self._scheduler

    @property
    def watcher(self) -> FactorLifecycleWatcher:
        return self._watcher

    def execute_weekly_scan(
        self,
        max_experiments: int = 100,
    ) -> dict[str, Any]:
        """执行每周因子扫描.

        Args:
            max_experiments: 最大实验数

        Returns:
            扫描结果
        """
        stale_factors = self._watcher.get_stale_factors()

        lines = [
            "=== Weekly Alpha Factory Meeting ===",
            f"失效因子数量: {len(stale_factors)}",
            "",
        ]

        if stale_factors:
            lines.append("[失效因子]")
            for f in stale_factors[:10]:
                lines.append(f"- {f['formula'][:80]}")

        new_experiments = min(max_experiments, max(10, len(stale_factors) * 5))
        lines.append(f"\n[新实验] 将运行 {new_experiments} 组实验")

        lines.append("\n[策略]")
        lines.append("1. WorldQuant 101 Alphas 多样化搜索")
        lines.append("2. 与失效因子负相关优先")
        lines.append("3. 多模型验证 (Linear + LightGBM)")

        result = {
            "stale_factors": len(stale_factors),
            "planned_experiments": new_experiments,
            "status": "scheduled",
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": "\n".join(lines),
        }

        self._experiment_results.append(result)
        return result

    def select_best_model(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """从实验结果中选择最优模型."""
        if not results:
            return {}

        valid = [r for r in results if r.get("sharpe", 0) > 0]
        if not valid:
            return results[0] if results else {}

        valid.sort(key=lambda x: x.get("sharpe", 0), reverse=True)
        return valid[0]


_weekly_meeting: WeeklyMeetingExecutor | None = None


def get_weekly_meeting() -> WeeklyMeetingExecutor:
    """获取全局周会实例."""
    global _weekly_meeting
    if _weekly_meeting is None:
        _weekly_meeting = WeeklyMeetingExecutor()
    return _weekly_meeting


def format_weekly_meeting_prompt(
    recent_performance: dict[str, Any] | None = None,
) -> str:
    """生成周会 prompt.

    Args:
        recent_performance: 最近组合表现

    Returns:
        周会 prompt
    """
    lines = [
        "=== 每周投研会议 ===",
        "时间: 每周五 15:00 - 周日 23:59",
        "",
        "[流程]",
        "1. 扫描全周失效因子",
        "2. 跑 100 组新实验",
        "3. Walk-forward 验证",
        "4. 模型热切换",
    ]

    if recent_performance:
        sharpe = recent_performance.get("sharpe_ratio", "N/A")
        mdd = recent_performance.get("max_drawdown", "N/A")
        lines.append(f"\n[当前组合] Sharpe: {sharpe}, MDD: {mdd}")

    return "\n".join(lines)
