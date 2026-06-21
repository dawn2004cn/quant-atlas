"""Lifecycle data-layer routes (tick, lineage, alignment)."""

from __future__ import annotations

from flask import Blueprint, request
from flask_login import login_required

from app.presentation.api.responses import success_response
from app.presentation.api.v1.lifecycle.runtime import get_tick_services
from app.presentation.api.v1_context import ApiV1Context


def register_lifecycle_data_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    _ = ctx

    @blueprint.post("/tick/ingest")
    @login_required
    def tick_ingest():
        data = request.get_json(silent=True) or {}
        svc, _, _ = get_tick_services()
        from app.modules.data.services.tick_data_service import TickRecord

        ticks = [TickRecord(**t) for t in data.get("ticks", [])]
        svc.ingest_batch(ticks)
        return success_response(data={"count": len(ticks)})

    @blueprint.get("/tick/recent/<symbol>/<market>")
    @login_required
    def tick_recent(symbol, market):
        svc, _, _ = get_tick_services()
        ticks = svc.get_recent_ticks(symbol, market)
        return success_response(data=ticks)

    @blueprint.get("/tick/orderbook/<symbol>/<market>")
    @login_required
    def tick_orderbook(symbol, market):
        svc, _, _ = get_tick_services()
        ob = svc.build_order_book(symbol, market)
        return success_response(data=ob)

    @blueprint.post("/lineage/record")
    @login_required
    def lineage_record():
        data = request.get_json(silent=True) or {}
        _, svc, _ = get_tick_services()
        from app.modules.data.services.tick_data_service import DataLineageNode

        svc.record_node(DataLineageNode(**data))
        return success_response()

    @blueprint.get("/lineage/trace/<order_id>")
    @login_required
    def lineage_trace(order_id):
        _, svc, _ = get_tick_services()
        return success_response(data=svc.get_lineage_graph(order_id))

    @blueprint.post("/alignment/align")
    @login_required
    def alignment_align():
        data = request.get_json(silent=True) or {}
        _, _, svc = get_tick_services()
        result = svc.align(
            symbol=str(data.get("symbol", "")),
            field=str(data.get("field", "close")),
            timestamp=str(data.get("timestamp", "")),
            source_values=data.get("source_values", {}),
        )
        return success_response(data=result)
