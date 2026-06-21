from __future__ import annotations

"""RD-Agent experiment HTTP routes."""

from flask import Blueprint, request
from flask_login import login_required

from app.application.errors import ValidationError
from app.presentation.api.common import ok_response, require_research_write_role
from app.presentation.api.request_parsers import parse_int_param
from app.presentation.api.v1_context import ApiV1Context


def register_rd_agent_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields
    enable_rd_agent = ctx.enable_rd_agent
    rdagent_run_service = ctx.rdagent_run_service

    @blueprint.post("/rd-agent/runs")
    @login_required
    def rd_agent_submit_run():
        if not enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")
        require_research_write_role()
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValidationError("JSON object required")
        out = rdagent_run_service.submit_run(body)
        return ok_response(
            data={
                **out,
                "poll_url": f"/api/v1/rd-agent/runs/{out['run_id']}",
                "artifacts_url": f"/api/v1/rd-agent/runs/{out['run_id']}/artifacts",
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/rd-agent/runs")
    @login_required
    def rd_agent_list_runs():
        if not enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")
        limit = parse_int_param(request.args.get("limit"), name="limit", default=50, min_value=1)
        limit = min(limit, 200)
        runs = rdagent_run_service.list_recent_runs(limit=limit)
        return ok_response(
            data={"runs": runs},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/rd-agent/runs/<run_id>")
    @login_required
    def rd_agent_get_run(run_id: str):
        if not enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")
        row = rdagent_run_service.get_run(run_id)
        if row is None:
            raise ValidationError("run not found")
        return ok_response(
            data=row,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/rd-agent/runs/<run_id>/artifacts")
    @login_required
    def rd_agent_get_artifacts(run_id: str):
        if not enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")
        payload = rdagent_run_service.get_artifacts(run_id)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
