from __future__ import annotations

"""Map API error codes to user-facing repair hints."""

from typing import Any

ActionableHint = dict[str, str]

_CATALOG: dict[str, ActionableHint] = {
    "market_service_unavailable": {
        "title": "行情服务未就绪",
        "body": "行情模块可能未启动或数据源暂时不可用。",
        "action_label": "打开集成中枢",
        "action_href": "/integration-hub",
        "action_kind": "link",
    },
    "mysql_not_enabled": {
        "title": "MySQL 未启用",
        "body": "当前环境未连接 MySQL，部分板块/入库能力不可用。",
        "action_label": "查看集成状态",
        "action_href": "/integration-hub",
        "action_kind": "link",
    },
    "timescaledb_not_enabled": {
        "title": "TimescaleDB 未启用",
        "body": "时序库未配置，历史 K 线高级查询可能受限。",
        "action_label": "运维文档",
        "action_href": "/observability",
        "action_kind": "link",
    },
    "context_unavailable": {
        "title": "服务上下文未初始化",
        "body": "应用可能仍在启动或部分模块未装配。",
        "action_label": "刷新页面",
        "action_href": "",
        "action_kind": "refresh",
    },
    "unauthorized": {
        "title": "需要登录",
        "body": "会话已过期或未登录。",
        "action_label": "去登录",
        "action_href": "/login",
        "action_kind": "link",
    },
    "internal_error": {
        "title": "服务器内部错误",
        "body": "可查看可观测性页或任务中心排查最近异常。",
        "action_label": "可观测性",
        "action_href": "/observability",
        "action_kind": "link",
    },
    "external_service_error": {
        "title": "外部依赖不可用",
        "body": "第三方数据源或消息队列可能中断，稍后重试或检查集成栈。",
        "action_label": "预警中心",
        "action_href": "/alert-center",
        "action_kind": "link",
    },
    "service_error": {
        "title": "后台服务异常",
        "body": "业务服务暂时不可用，可查看预警与任务消息。",
        "action_label": "任务中心",
        "action_href": "/task-center",
        "action_kind": "link",
    },
    "entity_not_found": {
        "title": "资源不存在",
        "body": "请确认代码、日期或 ID 是否正确。",
        "action_label": "返回首页",
        "action_href": "/",
        "action_kind": "link",
    },
    "not_found": {
        "title": "接口或页面不存在",
        "body": "请检查 URL 是否正确。",
        "action_label": "今日操盘台",
        "action_href": "/",
        "action_kind": "link",
    },
    "symbol_required": {
        "title": "缺少股票代码",
        "body": "请在焦点栏或表单中填写有效 symbol。",
        "action_label": "去自选股",
        "action_href": "/self-stocks",
        "action_kind": "link",
    },
    "symbol_and_peer_required": {
        "title": "对标比较缺少标的",
        "body": "请同时填写主标的与对标 peer 代码。",
        "action_label": "AI 诊股",
        "action_href": "/ai-analysis",
        "action_kind": "link",
    },
    "invalid_min_level": {
        "title": "告警级别参数无效",
        "body": "min_level 仅支持 info / warning / critical。",
        "action_label": "预警中心",
        "action_href": "/alert-center",
        "action_kind": "link",
    },
    "strategy_service not configured, enable Qlib or check ENABLE_QLIB": {
        "title": "Qlib 策略服务未启用",
        "body": "请设置 ENABLE_QLIB=1 并完成 Qlib 数据初始化。",
        "action_label": "集成中枢",
        "action_href": "/integration-hub",
        "action_kind": "link",
    },
    "data_stale": {
        "title": "行情或基础数据可能滞后",
        "body": "不建议基于过期数据做实盘决策，可触发基础数据刷新。",
        "action_label": "市场基础数据",
        "action_href": "/market-panorama",
        "action_kind": "link",
    },
}


def resolve_actionable_hints(
    *,
    code: str | None,
    message: str | None,
    details: dict[str, Any] | None = None,
) -> list[ActionableHint]:
    """Return zero or one primary repair hint for an API error payload."""
    del details
    keys = [k for k in (code, message) if k]
    for key in keys:
        hint = _CATALOG.get(key)
        if hint:
            return [dict(hint)]
    if code == "validation_error" and message:
        return [
            {
                "title": "请求未通过校验",
                "body": message,
                "action_label": "查看帮助",
                "action_href": "/capabilities",
                "action_kind": "link",
            }
        ]
    return []


def enrich_error_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Attach ``hints`` to standardized error payloads when known."""
    meta = payload.get("meta")
    err_str = payload.get("error", "")
    if isinstance(meta, dict):
        code = str(meta.get("code") or "")
        hints = resolve_actionable_hints(
            code=code,
            message=str(err_str or ""),
            details={k: v for k, v in meta.items() if k not in ("code", "request_id")},
        )
    else:
        err = payload.get("error")
        if isinstance(err, dict):
            hints = resolve_actionable_hints(
                code=str(err.get("code") or ""),
                message=str(err.get("message") or ""),
                details=err.get("details") if isinstance(err.get("details"), dict) else {},
            )
        else:
            return payload
    if hints:
        payload["hints"] = hints
    return payload
