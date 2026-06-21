from __future__ import annotations
"""API v1：Pytdx 全量接口封装（标准/扩展行情、读取、财务、交易、连接池）。"""


from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from ...application.errors import ValidationError
from app.modules.data.services.pytdx_api_service import PytdxApiService
from app.modules.data.services.pytdx_market_data_service import get_pytdx_market_data_service
from .common import ok_response
from .v1_context import ApiV1Context
from app.core.registry import register_routes


_svc = PytdxApiService()


@register_routes(name="pytdx", context="data", description="Pytdx 全量接口封装")
def register_pytdx_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/pytdx/catalog")
    @login_required
    def pytdx_catalog():
        """能力目录，对照 Pytdx 文档模块划分。"""
        return ok_response(
            data={
                "doc": "https://pytdx-docs.readthedocs.io/zh-cn/latest/",
                "modules": _svc.catalog(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/pytdx/status")
    @login_required
    def pytdx_status():
        """各子模块连接/配置状态。"""
        return ok_response(
            data=_svc.status(),
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    _ALLOWED_MODULES = {"hq", "exhq", "reader", "finance", "trade", "pool"}

    def _invoke_body() -> tuple[str, str, list[Any], dict[str, Any]]:
        body = request.get_json(silent=True) or {}
        module = str(body.get("module") or request.view_args.get("module") or "").strip().lower()
        method = str(body.get("method") or "").strip()
        if not module or not method:
            raise ValidationError("module and method are required")
        if module not in _ALLOWED_MODULES:
            raise ValidationError(f"module must be one of: {', '.join(sorted(_ALLOWED_MODULES))}")
        args = body.get("args") or []
        kwargs = body.get("kwargs") or {}
        if not isinstance(args, list):
            raise ValidationError("args must be a list")
        if not isinstance(kwargs, dict):
            raise ValidationError("kwargs must be an object")
        return module, method, args, kwargs

    @blueprint.post("/pytdx/invoke")
    @login_required
    def pytdx_invoke():
        """通用调用：``{ module, method, args, kwargs }``。"""
        module, method, args, kwargs = _invoke_body()
        try:
            result = _svc.invoke(module, method, args, kwargs)
        except Exception as exc:
            raise ValidationError(f"pytdx_invoke_failed: {exc}") from exc
        return ok_response(
            data={"module": module, "method": method, "result": result},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/pytdx/<module>/invoke")
    @login_required
    def pytdx_invoke_module(module: str):
        """按模块调用，body: ``{ method, args, kwargs }``。"""
        body = request.get_json(silent=True) or {}
        method = str(body.get("method") or "").strip()
        if not method:
            raise ValidationError("method is required")
        args = body.get("args") or []
        kwargs = body.get("kwargs") or {}
        try:
            result = _svc.invoke(module, method, args, kwargs)
        except Exception as exc:
            raise ValidationError(f"pytdx_invoke_failed: {exc}") from exc
        return ok_response(
            data={"module": module, "method": method, "result": result},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/pytdx/hq/quotes")
    @login_required
    def pytdx_hq_quotes():
        """便捷：批量实时行情。body: ``{ symbols: [\"600519\", \"sh600519\", ...] }``。"""
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols") or []
        if not isinstance(symbols, list) or not symbols:
            raise ValidationError("symbols must be a non-empty list")
        try:
            rows = _svc.hq_quotes([str(s) for s in symbols])
        except Exception as exc:
            raise ValidationError(f"pytdx_hq_quotes_failed: {exc}") from exc
        return ok_response(
            data={"items": rows, "count": len(rows)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/pytdx/market/snapshot")
    @login_required
    def pytdx_market_snapshot():
        """便捷：状态 + 行情 + 样本日K/财务。body: ``{ symbols: [\"600519\"] }``。"""
        body = request.get_json(silent=True) or {}
        symbols = body.get("symbols") or ["600519", "000001"]
        if not isinstance(symbols, list):
            raise ValidationError("symbols must be a list")
        try:
            data = _svc.market_snapshot([str(s) for s in symbols])
        except Exception as exc:
            raise ValidationError(f"pytdx_snapshot_failed: {exc}") from exc
        return ok_response(data=data, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/pytdx/market/daily-bars/<symbol>")
    @login_required
    def pytdx_daily_bars(symbol: str):
        count = int(request.args.get("count", 60))
        rows = get_pytdx_market_data_service().get_daily_bars(symbol, count=count)
        return ok_response(
            data={"symbol": symbol, "items": rows, "count": len(rows)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/pytdx/market/finance/<symbol>")
    @login_required
    def pytdx_finance(symbol: str):
        fin = get_pytdx_market_data_service().get_finance_info(symbol)
        return ok_response(
            data={"symbol": symbol, "finance": fin},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
