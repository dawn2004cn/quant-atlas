from __future__ import annotations
"""Post-Mortem Analysis - failure溯源 for rd-agent research.

This implements Section 2E from the roadmap:
- 失败溯源: Analyze why a factor experiment failed
- Traceback analysis: Identify the type of error
- 智能补丁: Auto-patch prompts based on failure type
"""


from enum import Enum
from typing import Any


class FailureType(Enum):
    """Types of research failures."""

    FACTOR_EXPRESSION_ERROR = "factor_expression_error"
    BACKTEST_ERROR = "backtest_error"
    DATA_ERROR = "data_error"
    OVERFITTING = "overfitting"
    INSUFFICIENT_DATA = "insufficient_data"
    LOW_PERFORMANCE = "low_performance"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class PostMortemAnalysis:
    """Post-mortem analysis for failed factor experiments."""

    def __init__(self) -> None:
        self._failure_history: list[dict[str, Any]] = []

    def analyze(
        self,
        formula: str,
        error_message: str | None = None,
        backtest_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Analyze a failed experiment and determine failure type.

        Args:
            formula: The alpha expression that failed
            error_message: Error message or traceback
            backtest_result: Backtest result (may contain error info)

        Returns:
            Analysis result with failure_type, root_cause, and patch_prompt
        """
        failure_type = self._detect_failure_type(error_message, backtest_result)
        root_cause = self._determine_root_cause(failure_type, error_message)
        patch_prompt = self._generate_patch_prompt(failure_type, root_cause, formula)

        analysis = {
            "formula": formula,
            "failure_type": failure_type.value,
            "root_cause": root_cause,
            "patch_prompt": patch_prompt,
            "error_message": error_message,
        }

        self._failure_history.append(analysis)
        return analysis

    def _detect_failure_type(
        self,
        error_message: str | None,
        backtest_result: dict[str, Any] | None,
    ) -> FailureType:
        """Detect the type of failure."""
        err = (error_message or "").lower()
        bt = backtest_result or {}

        if "expression" in err or "syntax" in err:
            return FailureType.FACTOR_EXPRESSION_ERROR
        if "keyerror" in err or "attribute" in err:
            return FailureType.DATA_ERROR
        if "timeout" in err:
            return FailureType.TIMEOUT

        sharpe = bt.get("sharpe_ratio", 0)
        mdd = bt.get("max_drawdown", 0)
        if sharpe <= 0 or abs(mdd) > 0.5:
            return FailureType.LOW_PERFORMANCE
        if abs(mdd) > 0.3:
            return FailureType.OVERFITTING

        return FailureType.UNKNOWN

    def _determine_root_cause(
        self,
        failure_type: FailureType,
        error_message: str | None,
    ) -> str:
        """Determine the root cause of the failure."""
        causes = {
            FailureType.FACTOR_EXPRESSION_ERROR: "因子表达式语法错误或使用了不支持的算子",
            FailureType.BACKTEST_ERROR: "回测执行时出错",
            FailureType.DATA_ERROR: "数据缺失或不完整",
            FailureType.OVERFITTING: "因子过拟合，泛化能力差",
            FailureType.INSUFFICIENT_DATA: "训练数据不足",
            FailureType.LOW_PERFORMANCE: "因子收益低或不稳定",
            FailureType.TIMEOUT: "计算超时",
            FailureType.UNKNOWN: error_message or "未知错误",
        }
        return causes.get(failure_type, "未知错误")

    def _generate_patch_prompt(
        self,
        failure_type: FailureType,
        root_cause: str,
        formula: str,
    ) -> str:
        """Generate a patched prompt for the next attempt."""
        patches = {
            FailureType.FACTOR_EXPRESSION_ERROR: (
                f"[PATCH] 修复因子表达式错误:\n"
                f"- 原公式: {formula}\n"
                f"- 检查算子是否正确\n"
                f"- 使用 WorldQuant 101 Alpha 库中的验证模板\n"
            ),
            FailureType.BACKTEST_ERROR: (
                "[PATCH] 修复回测错误:\n"
                "- 检查回测参数是否正确\n"
                "- 减少 lookback 或 window 参数\n"
            ),
            FailureType.DATA_ERROR: (
                "[PATCH] 修复数据错误:\n"
                "- 使用更稳健的数据源\n"
                "- 添加数据验证逻辑\n"
            ),
            FailureType.OVERFITTING: (
                "[PATCH] 防止过拟合:\n"
                "- 增加训练窗口\n"
                "- 减少因子复杂度\n"
                "- 使用 walk-forward 验证\n"
            ),
            FailureType.LOW_PERFORMANCE: (
                "[PATCH] 提升性能:\n"
                "- 尝试另一个 Alpha 类别\n"
                "- 与现有组合寻求负相关\n"
                "- 结合多个短周期因子\n"
            ),
            FailureType.TIMEOUT: (
                "[PATCH] 优化性能:\n"
                "- 减少计算窗口\n"
                "- 使用简化算子\n"
            ),
        }
        base_patch = patches.get(failure_type, "[PATCH] 检查并修复问题后重试")
        return base_patch

    def get_failure_history(
        self,
        *,
        limit: int = 20,
        failure_type: FailureType | None = None,
    ) -> list[dict[str, Any]]:
        """Get failure history for analysis."""
        history = self._failure_history
        if failure_type:
            history = [h for h in history if h.get("failure_type") == failure_type.value]
        return history[-limit:]


_global_postmortem: PostMortemAnalysis | None = None


def get_postmortem_analyzer() -> PostMortemAnalysis:
    """Get global post-mortem analyzer."""
    global _global_postmortem
    if _global_postmortem is None:
        _global_postmortem = PostMortemAnalysis()
    return _global_postmortem
