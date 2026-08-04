from __future__ import annotations

"""Compact operational health banner for workbench and global UI."""

from typing import Any

from app.core.logger import get_logger
from app.core.runtime_config import get_runtime_int
from app.modules.system.services.system.alert_center_service import AlertCenterService

logger = get_logger(__name__)


class SystemHealthBannerService:
    """Aggregate alert center, integration stack and task digest into one banner DTO."""

    def __init__(self, *, alert_service: AlertCenterService | None = None) -> None:
        self._alert_service = alert_service or AlertCenterService()

    def build_banner(
        self,
        *,
        integration: dict[str, Any] | None = None,
        task_digest: dict[str, Any] | None = None,
        quotes_dump: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        integration = integration or {}
        task_digest = task_digest or {}
        quotes_dump = quotes_dump or {}
        critical = 0
        warning = 0
        messages: list[str] = []
        stale = False
        try:
            feed = self._alert_service.list_alerts(limit=30, min_level="warning")
            critical = int(feed.counts_by_level.get("critical", 0))
            warning = int(feed.counts_by_level.get("warning", 0))
            for item in feed.items[:4]:
                if item.level in ("critical", "warning"):
                    messages.append(item.title or item.message)
                if item.category == "data":
                    stale = True
        except Exception as exc:
            logger.debug("system_health_banner alerts: %s", exc)

        issue_count = int(integration.get("issue_count") or 0)
        fail_n = int(task_digest.get("fail_or_warn") or 0)
        if issue_count:
            warning += issue_count
            messages.append(f"集成栈 {issue_count} 项待处理")
        if fail_n:
            warning += 1
            messages.append(f"近期任务异常 {fail_n} 条")

        dump_n = int(quotes_dump.get("full_dump_count") or 0)
        dump_threshold = max(1, int(get_runtime_int("QUOTES_FULL_DUMP_WARN_THRESHOLD", 1)))
        dump_warn = dump_n >= dump_threshold
        if dump_warn:
            warning += 1
            messages.append(
                f"全量 /quotes dump 累计 {dump_n} 次（阈值≥{dump_threshold}），请改用 quotes/page"
            )

        level = "ok"
        if critical > 0:
            level = "critical"
        elif warning > 0:
            level = "warning"

        allow_live = level != "critical"
        if level == "critical":
            message = messages[0] if messages else "存在严重告警，建议暂停实盘操作"
        elif level == "warning":
            message = messages[0] if messages else "部分子系统需关注，请查看预警中心"
        else:
            message = "系统运行正常，数据与任务链路未发现阻断项"

        return {
            "level": level,
            "message": message[:200],
            "allow_live_trading": allow_live,
            "critical_count": critical,
            "warning_count": warning,
            "stale_data": stale,
            "quotes_full_dump_count": dump_n,
            "quotes_full_dump_warn": dump_warn,
            "quotes_full_dump_threshold": dump_threshold,
        }
