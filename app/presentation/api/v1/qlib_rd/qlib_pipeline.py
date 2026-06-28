from __future__ import annotations

"""Qlib pipeline and research snapshot HTTP routes."""

import uuid

from flask import Blueprint, Response, request, stream_with_context
from flask_login import login_required

from app.application.errors import ValidationError
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.modules.data.services.research_pipeline_snapshot import build_research_pipeline_snapshot
from app.presentation.api.common import (
    ok_resource,
    ok_response,
    parse_market,
    require_research_write_role,
)
from app.presentation.api.request_parsers import (
    parse_bool_param,
    parse_float_param,
    parse_int_param,
    parse_optional_bool_param,
)
from app.presentation.api.v1_context import ApiV1Context

logger = get_logger(__name__)


def register_qlib_pipeline_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    enable_qlib = ctx.enable_qlib
    enable_rd_agent = ctx.enable_rd_agent
    enable_celery = ctx.enable_celery
    qlib_pipeline_service = ctx.qlib_pipeline_service
    rdagent_run_service = ctx.rdagent_run_service
    task_dispatcher = ctx.task_dispatcher
    task_message_store = ctx.task_message_store

    @blueprint.get("/qlib/health")
    def qlib_health():
        """Qlib / RD-Agent 路线图开关状态（不 import qlib，供监控与前端探测）。"""
        return ok_response(
            data={
                "qlib_enabled": enable_qlib,
                "rd_agent_enabled": enable_rd_agent,
                "roadmap_doc": "docs/roadmap_qlib_rd_agent.md",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/qlib/status")
    def qlib_status():
        """导出目录、元数据、是否可 import pyqlib（不强制安装）。"""
        st = qlib_pipeline_service.status()
        st["enable_qlib"] = enable_qlib
        st["enable_rd_agent"] = enable_rd_agent
        return ok_response(
            data=st,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/research/pipeline-status")
    @login_required
    def research_pipeline_status():
        """研究闭环步骤状态：Qlib、RD 最近 run、qlib_gate；供 ``/research-pipeline`` 页轮询。"""
        snap = build_research_pipeline_snapshot(
            enable_qlib=enable_qlib,
            enable_rd_agent=enable_rd_agent,
            qlib_pipeline_service=qlib_pipeline_service,
            rdagent_run_service=rdagent_run_service,
        )
        return ok_response(
            data=snap,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/qlib/ingest")
    @login_required
    def qlib_ingest():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")
        require_research_write_role()
        payload = request.get_json(silent=True) or {}
        symbols = payload.get("symbols") or []
        if isinstance(symbols, str):
            symbols = [symbols]
        symbols = [str(s).strip() for s in symbols if str(s).strip()]
        if not symbols:
            raise ValidationError("symbols is required (non-empty list)")
        market = parse_market(payload.get("market", "CN"))
        if market != MarketCode.CN:
            raise ValidationError("ingest currently supports CN market only")
        period = (payload.get("period") or "2y").strip()
        merge_existing = parse_bool_param(
            payload.get("merge_existing"),
            name="merge_existing",
            default=False,
        )
        meta = qlib_pipeline_service.ingest_symbols(
            symbols,
            market,
            period=period,
            merge_existing=merge_existing,
        )
        data = meta.to_dict()
        if parse_bool_param(
            payload.get("dump_bin") or payload.get("dump_bin_after"),
            name="dump_bin",
            default=False,
        ):
            mw = parse_int_param(
                payload.get("dump_bin_max_workers"),
                name="dump_bin_max_workers",
                default=8,
                min_value=1,
            )
            ow = parse_bool_param(payload.get("dump_bin_overwrite"), name="dump_bin_overwrite", default=False)
            inc = parse_optional_bool_param(
                payload.get("dump_bin_incremental"),
                name="dump_bin_incremental",
            )
            data["qlib_bin"] = qlib_pipeline_service.dump_to_qlib_bin(
                max_workers=mw,
                overwrite=ow,
                incremental=inc,
            )
        return ok_response(
            data=data,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/qlib/dump_bin")
    @login_required
    def qlib_dump_bin():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")
        require_research_write_role()
        payload = request.get_json(silent=True) or {}
        mw = parse_int_param(
            payload.get("max_workers"),
            name="max_workers",
            default=8,
            min_value=1,
        )
        ow = parse_bool_param(payload.get("overwrite"), name="overwrite", default=False)
        inc = parse_optional_bool_param(payload.get("incremental"), name="incremental")
        out = qlib_pipeline_service.dump_to_qlib_bin(max_workers=mw, overwrite=ow, incremental=inc)
        return ok_response(
            data=out,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/qlib/update_all")
    @login_required
    def qlib_update_all():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")
        require_research_write_role()
        body = request.get_json(silent=True) or {}
        period = str(body.get("period") or "2y").strip()
        mw = parse_int_param(body.get("max_workers"), name="max_workers", default=8, min_value=1)
        inc = parse_optional_bool_param(body.get("dump_incremental"), name="dump_incremental")
        sync = parse_bool_param(request.args.get("sync"), name="sync", default=False)
        if enable_celery and not sync:
            try:
                from app.celery_app import celery as _c
                from app.tasks.qlib_data_update import qlib_incremental_pipeline

                if (
                    _c is not None
                    and qlib_incremental_pipeline is not None
                    and hasattr(qlib_incremental_pipeline, "delay")
                ):
                    _, task_id, enqueued = task_dispatcher.dispatch(
                        qlib_incremental_pipeline,
                        task_name="app.tasks.qlib_data_update.qlib_incremental_pipeline",
                        kwargs={"period": period, "max_workers": mw, "dump_incremental": inc},
                        bucket_seconds=120,
                        ttl_seconds=1200,
                    )
                    if not enqueued:
                        return ok_response(
                            data={
                                "mode": "async",
                                "task_id": task_id,
                                "deduplicated": True,
                                "label": task_dispatcher.get_task_label(
                                    "app.tasks.qlib_data_update.qlib_incremental_pipeline"
                                ),
                            },
                            legacy_alias_key=None,
                            enable_legacy_alias=legacy,
                        )
                    task_message_store.push(
                        event="task_queued",
                        task_id=task_id,
                        task_name="app.tasks.qlib_data_update.qlib_incremental_pipeline",
                        detail=f"已投递 Qlib 增量管线（TDX 等多源→CSV→bin）period={period}",
                        meta={"period": period, "max_workers": mw},
                    )
                    return ok_response(
                        data={
                            "mode": "async",
                            "task_id": task_id,
                            "label": task_dispatcher.get_task_label(
                                "app.tasks.qlib_data_update.qlib_incremental_pipeline"
                            ),
                        },
                        legacy_alias_key=None,
                        enable_legacy_alias=legacy,
                    )
                raise RuntimeError("celery_not_available")
            except Exception as exc:
                logger.warning("qlib update_all celery enqueue failed, sync fallback: %s", exc)

        from app.tasks.qlib_data_update import update_all_data

        out = update_all_data(period=period, max_workers=mw, dump_incremental=inc)
        ok = bool(out.get("ok"))
        task_message_store.push(
            event="task_succeeded" if ok else "task_failed",
            task_id=f"sync-{uuid.uuid4().hex[:12]}",
            task_name="inline.qlib_incremental_pipeline",
            detail=str(out.get("message") or out.get("error") or ("ok" if ok else "failed"))[:500],
            meta={"mode": "sync", "ok": ok},
        )
        return ok_response(
            data={**out, "mode": "sync"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/qlib/factors")
    @login_required
    def qlib_factors():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")
        symbol = (request.args.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol is required")
        market = parse_market(request.args.get("market", "CN"))
        start = (request.args.get("start") or "").strip() or None
        end = (request.args.get("end") or "").strip() or None
        out = qlib_pipeline_service.factors(symbol, market, start=start, end=end)
        return ok_response(
            data=out,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/qlib/backtest")
    @login_required
    def qlib_backtest():
        if not enable_qlib:
            raise ValidationError("ENABLE_QLIB is not enabled")
        payload = request.get_json(silent=True) or {}
        symbol = (payload.get("symbol") or "").strip()
        if not symbol:
            raise ValidationError("symbol is required")
        start = (payload.get("start") or "").strip()
        end = (payload.get("end") or "").strip()
        if not start or not end:
            raise ValidationError("start and end are required (YYYY-MM-DD)")
        market = parse_market(payload.get("market", "CN"))
        initial_capital = parse_float_param(
            payload.get("initial_capital"),
            name="initial_capital",
            default=100_000,
            min_value=0,
        )
        result = qlib_pipeline_service.unified_buy_hold_backtest(
            symbol,
            market,
            start=start,
            end=end,
            initial_capital=initial_capital,
        )
        return ok_resource(
            resource=result,
            resource_key="backtest_result",
            enable_legacy_alias=legacy,
            metrics=result.get("metrics", {}),
            trades=result.get("trades", []),
        )

    @blueprint.get("/qlib/progress/<run_id>")
    @login_required
    def qlib_progress_sse(run_id: str):
        """SSE endpoint: stream qlib/rdagent factor loop progress for a run.

        Subscribes to Redis PubSub ``sse:qlib:progress:{run_id}`` and
        forwards events as SSE ``data:`` lines.  Timeouts after 30s of silence.
        """
        import json
        import os
        import time

        from redis import Redis

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

        def event_stream():
            client: Redis | None = None
            try:
                client = Redis.from_url(url, decode_responses=True)
                pubsub = client.pubsub()
                pubsub.subscribe(f"sse:qlib:progress:{run_id}")
                deadline = time.monotonic() + 30
                for message in pubsub.listen():
                    if time.monotonic() > deadline:
                        yield "data: {\"pct\": 0, \"message\": \"timeout\"}\n\n"
                        return
                    if message["type"] != "message":
                        continue
                    deadline = time.monotonic() + 30
                    yield f"data: {message['data']}\n\n"
            except Exception as exc:
                yield f"data: {json.dumps({'pct': 0, 'message': str(exc)})}\n\n"
            finally:
                if client is not None:
                    try:
                        pubsub.unsubscribe()
                        client.close()
                    except Exception:
                        logger.debug("Redis pubsub cleanup failed", exc_info=True)

        return Response(
            stream_with_context(event_stream()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
