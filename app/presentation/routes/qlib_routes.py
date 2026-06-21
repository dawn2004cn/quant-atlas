from __future__ import annotations
"""Qlib SDK 能力 HTTP 接口（init / 数据状态 / 官方回测 / 策略信号对齐）。"""


from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_login import login_required

from ...application.errors import ValidationError
from ...application.services.qlib.qlib_service import QlibService
from ..api.response_builders import build_success_payload, with_legacy_aliases


def _ok(*, enable_legacy: bool, **payload):
    if "data" in payload:
        data = payload.pop("data")
        out = build_success_payload(data=data, meta=payload or None)
        return with_legacy_aliases(out, alias_key=None, enabled=enable_legacy)
    out = build_success_payload(data=payload)
    return with_legacy_aliases(out, alias_key=None, enabled=enable_legacy)


def create_qlib_sdk_blueprint(
    qlib_service: QlibService,
    *,
    enable_qlib: bool = False,
    enable_legacy_response_fields: bool = False,
) -> Blueprint:
    bp = Blueprint("qlib_sdk", __name__, url_prefix="/api/v1/qlib/sdk")

    def _require():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")

    @bp.post("/init")
    @login_required
    def qlib_sdk_init():
        _require()
        body = request.get_json(silent=True) or {}
        cfg = body.get("config_path") or body.get("yaml_path")
        path = Path(str(cfg).strip()) if cfg else None
        provider_uri = body.get("provider_uri")
        region = body.get("region")
        extra = body.get("extra") if isinstance(body.get("extra"), dict) else None
        data = qlib_service.init_qlib(
            path,
            provider_uri=provider_uri,
            region=region,
            extra=extra,
        )
        return jsonify(_ok(data=data, enable_legacy=enable_legacy_response_fields))

    @bp.get("/data_status")
    @login_required
    def qlib_sdk_data_status():
        _require()
        market = (request.args.get("market") or "CN").strip()
        data = qlib_service.get_data_status(market=market)
        return jsonify(_ok(data=data, enable_legacy=enable_legacy_response_fields))

    @bp.post("/backtest")
    @login_required
    def qlib_sdk_backtest():
        _require()
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValidationError("JSON body required")
        data = qlib_service.run_qlib_backtest(body)
        return jsonify(_ok(data=data, enable_legacy=enable_legacy_response_fields))

    @bp.post("/integrate_strategy")
    @login_required
    def qlib_sdk_integrate():
        _require()
        body = request.get_json(silent=True) or {}
        if body is None:
            raise ValidationError("JSON body required")
        data = qlib_service.integrate_existing_strategy(body)
        return jsonify(_ok(data=data, enable_legacy=enable_legacy_response_fields))

    return bp
