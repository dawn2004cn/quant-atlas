from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Failure Memory Service - 自动分析错误并存储修复策略."""


import traceback
from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode

logger = get_logger(__name__)


class FailureRecord:
    """失败记录"""

    def __init__(
        self,
        id: str,
        task_id: str,
        error_type: str,
        error_message: str,
        error_trace: str,
        fix_strategy: str | None = None,
        created_at: datetime | None = None,
    ):
        self.id = id
        self.task_id = task_id
        self.error_type = error_type
        self.error_message = error_message
        self.error_trace = error_trace
        self.fix_strategy = fix_strategy
        self.created_at = created_at or datetime.now()


class FailureMemoryService:
    """失败经验归档服务"""

    def __init__(self, memory_store: object = None):
        self._memory_store = memory_store or {}
        self._fix_strategies = self._load_common_fixes()

    def record_failure(
        self,
        task_id: str,
        error: Exception,
        context: dict[str, Any],
    ) -> FailureRecord:
        """记录失败并尝试自动修复"""

        error_type = type(error).__name__
        error_message = str(error)
        error_trace = traceback.format_exc()

        record = FailureRecord(
            id=f"fail_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            error_type=error_type,
            error_message=error_message,
            error_trace=error_trace,
        )

        # 尝试分析错误并生成修复策略
        fix_strategy = self._analyze_and_fix(error, context)
        if fix_strategy:
            record.fix_strategy = fix_strategy
            self._store_fix(record)

        logger.warning(f"Failure recorded: {task_id} - {error_type}: {error_message[:100]}")

        return record

    def _analyze_and_fix(self, error: Exception, context: dict[str, Any]) -> str | None:
        """分析错误并生成修复策略"""

        error_type = type(error).__name__
        error_msg = str(error).lower()

        # 常见的错误类型和修复策略
        fixes = {
            "NameError": self._fix_name_error(error_msg, context),
            "SyntaxError": "检查策略代码语法，确保Python语法正确",
            "ImportError": "检查导入的模块是否已安装，或使用替代模块",
            "KeyError": self._fix_key_error(error_msg, context),
            "ValueError": "检查参数值类型和范围是否正确",
            "TimeoutError": "增加超时时间或简化计算逻辑",
            "ConnectionError": "检查网络连接或使用本地缓存数据",
            "OutOfMemoryError": "减少数据量或使用分批处理",
            "ZeroDivisionError": "添加除数检查，避免除以零",
            "IndexError": "检查索引范围是否越界",
            "AttributeError": "检查对象是否有该属性",
            "TypeError": "检查数据类型是否匹配",
        }

        fix = fixes.get(error_type)
        if fix:
            return fix

        # 检查常见错误关键词
        if "timeout" in error_msg:
            return "增加API超时时间，或使用缓存数据作为降级方案"
        if "permission" in error_msg:
            return "检查文件/数据访问权限"
        if "not found" in error_msg:
            return "检查资源路径是否正确"
        if "invalid" in error_msg:
            return "验证输入参数是否有效"

        return None

    def _fix_name_error(self, error_msg: str, context: dict) -> str:
        """修复NameError"""
        if "未定义" in error_msg or "undefined" in error_msg:
            return "声明缺失的变量或函数，或检查导入语句"
        return "检查变量/函数名称拼写是否正确"

    def _fix_key_error(self, error_msg: str, context: dict) -> str:
        """修复KeyError"""
        if "metrics" in error_msg:
            return "在访问metrics前检查字段是否存在，使用.get()方法提供默认值"
        return "检查字典键是否存在于访问前"

    def _store_fix(self, record: FailureRecord) -> None:
        """存储修复策略到记忆库"""
        if not self._memory_store:
            return

        key = f"fix:{record.error_type}"
        if key not in self._memory_store:
            self._memory_store[key] = []

        self._memory_store[key].append({
            "error": record.error_message[:200],
            "fix": record.fix_strategy,
            "task_id": record.task_id,
            "timestamp": record.created_at.isoformat(),
        })

        logger.info(f"Stored fix strategy for {record.error_type}")

    def _load_common_fixes(self) -> GenericResponseDTO[str, str]:
        """加载常见修复策略"""
        return {
            "NameError": "检查变量是否已定义",
            "SyntaxError": "修复代码语法错误",
            "ImportError": "检查依赖是否安装",
            "KeyError": "使用.get()方法安全访问",
            "TimeoutError": "增加超时或使用缓存",
        }

    def get_fix_suggestion(self, error_type: str) -> str | None:
        """获取错误类型的修复建议"""
        return self._fix_strategies.get(error_type)

    def get_recent_fixes(self, limit: int = 10) -> list[dict]:
        """获取最近的修复记录"""
        all_fixes = []
        for key, values in self._memory_store.items():
            if key.startswith("fix:"):
                all_fixes.extend(values)

        all_fixes.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_fixes[:limit]


def create_failure_memory_service() -> FailureMemoryService:
    """创建失败记忆服务实例"""
    return FailureMemoryService()