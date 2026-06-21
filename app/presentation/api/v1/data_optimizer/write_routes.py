"""Data write-result route."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ExternalServiceError, ValidationError
from app.modules.data.services.data_router_service import MarketDataService
from app.modules.data.services.history_row_validator import validate_ohlcv_history_rows
from app.modules.strategy.services.strategy.scenario_optimizer_service import ScenarioBasedDataService
from app.presentation.api.common import ok_resource
from app.presentation.api.v1_context import ApiV1Context


def register_data_optimizer_write_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.post("/data/write-result")
    @login_required
    def data_write_result():
        """Persist OHLCV rows to MySQL (WRITER_RESULT scenario)."""
        body = request.get_json(silent=True) or {}
        symbol = str(body.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol_required")

        raw_rows = body.get("rows") if "rows" in body else body.get("data")
        rows = validate_ohlcv_history_rows(raw_rows)

        service = ScenarioBasedDataService(market_data_service=MarketDataService())
        ok = service.write_result(symbol, rows)
        if not ok:
            raise ExternalServiceError("write_result_failed")

        return ok_resource(
            resource={
                "ok": True,
                "symbol": symbol,
                "rows_written": len(rows),
            },
            resource_key="write_result",
            enable_legacy_alias=False,
        )
