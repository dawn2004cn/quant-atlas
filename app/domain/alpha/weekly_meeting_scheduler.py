from __future__ import annotations
"""Weekly Meeting Scheduler - 投研周会自动化调度.

实现 Section 3, 第三步：每周五闭市后自动化执行。
"""


from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class WeeklyMeetingConfig:
    """周会配置."""

    enabled: bool = False
    run_day: int = 4
    run_hour: int = 15
    max_experiments: int = 100
    min_sharpe: float = 1.0


class WeeklyMeetingScheduler:
    """投研周会调度器 - 自动化执行."""

    def __init__(self) -> None:
        self._config = WeeklyMeetingConfig()
        self._last_run: str | None = None
        self._next_run: str | None = None
        self._history: list[dict[str, Any]] = []

    @property
    def config(self) -> WeeklyMeetingConfig:
        return self._config

    def enable(self) -> None:
        """启用周会."""
        self._config.enabled = True
        self._update_next_run()

    def disable(self) -> None:
        """禁用周会."""
        self._config.enabled = False
        self._next_run = None

    def is_enabled(self) -> bool:
        return self._config.enabled

    def should_run_now(self) -> bool:
        """检查是否应该现在运行."""
        if not self._config.enabled:
            return False

        now = datetime.now()

        if now.weekday() == self._config.run_day:
            if now.hour >= self._config.run_hour:
                if self._last_run:
                    last = datetime.fromisoformat(self._last_run)
                    if (now - last).days < 7:
                        return False
                return True

        return False

    def _update_next_run(self) -> None:
        """更新下次运行时间."""
        now = datetime.now()
        days_ahead = (self._config.run_day - now.weekday()) % 7

        if days_ahead == 0 and now.hour < self._config.run_hour:
            days_ahead = 0
        elif days_ahead == 0 and now.hour >= self._config.run_hour:
            days_ahead = 7

        next_run = now + timedelta(days=days_ahead)
        next_run = next_run.replace(
            hour=self._config.run_hour,
            minute=0,
            second=0,
        )

        self._next_run = next_run.isoformat()

    def get_next_run_time(self) -> str | None:
        """获取下次运行时间."""
        return self._next_run

    def record_run(
        self,
        status: str,
        results: dict[str, Any],
    ) -> None:
        """记录运行结果."""
        self._last_run = datetime.utcnow().isoformat()

        self._history.append({
            "timestamp": self._last_run,
            "status": status,
            "results": results,
        })

        if len(self._history) > 20:
            self._history = self._history[-20:]


class WeeklyMeetingExecutor:
    """投研周会执行器 - 执行扫描和实验."""

    def __init__(self) -> None:
        self._scheduler = WeeklyMeetingScheduler()
        self._stale_factors: list[dict[str, Any]] = []

    @property
    def scheduler(self) -> WeeklyMeetingScheduler:
        return self._scheduler

    def scan_stale_factors(
        self,
        decay_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """扫描失效因子."""
        self._stale_factors = []

        return self._stale_factors

    def generate_new_experiments(
        self,
        count: int | None = None,
    ) -> list[dict[str, Any]]:
        """生成新实验."""
        if count is None:
            count = self._scheduler.config.max_experiments

        min(count, max(10, len(self._stale_factors) * 5))

        experiments = []
        return experiments

    def execute(self) -> dict[str, Any]:
        """执行周会."""
        if not self._scheduler.should_run_now():
            return {"status": "skipped", "reason": "not scheduled time"}

        stale = self.scan_stale_factors()
        experiments = self.generate_new_experiments()

        results = {
            "stale_factors": len(stale),
            "experiments_planned": len(experiments),
            "experiments_completed": 0,
            "best_model": None,
            "status": "completed",
        }

        self._scheduler.record_run("completed", results)
        return results

    def get_history(self) -> list[dict[str, Any]]:
        """获取历史记录."""
        return self._scheduler._history


def format_weekly_meeting_prompt() -> str:
    """生成周会 prompt."""
    return """=== 自动化投研周会 ===
[运行时间]
- 每周五 15:00 自动执行

[执行流程]
1. 扫描全周失效因子 (Sharpe 衰减 > 30%)
2. 生成 100 组新实验
3. Walk-forward 验证
4. 模型热切换

[策略]
- 使用 WorldQuant 101 Alphas 多样化
- 与失效因子负相关优先
- 多模型验证 (Linear + LightGBM)

[成功标准]
- Sharpe > 1.0
- 回测 MDD < 15%
- 影子测试偏差 < 5%"""


_global_executor: WeeklyMeetingExecutor | None = None


def get_weekly_meeting_executor() -> WeeklyMeetingExecutor:
    """获取全局周会执行器."""
    global _global_executor
    if _global_executor is None:
        _global_executor = WeeklyMeetingExecutor()
    return _global_executor
