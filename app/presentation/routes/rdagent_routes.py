from __future__ import annotations

"""RD-Agent 兼容路由：``/api/rdagent/*``（推荐新客户端改用 ``/api/v1/rd-agent/*``）。"""


from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from ...application.errors import ValidationError
from ...application.services.research.rdagent_run_service import RDAgentRunService
from ..api.response_builders import build_success_payload, with_legacy_aliases


def create_rdagent_blueprint(
    *,
    rdagent_run_service: RDAgentRunService,
    enable_rd_agent: bool = False,
    enable_legacy_response_fields: bool = False,
) -> Blueprint:
    bp = Blueprint("rdagent_api", __name__, url_prefix="/api")

    def _wrap(data: dict, meta: dict | None = None):
        payload = build_success_payload(data=data, meta=meta)
        return jsonify(with_legacy_aliases(payload, alias_key=None, enabled=enable_legacy_response_fields))

    def _require():
        if not enable_rd_agent:
            raise ValidationError("ENABLE_RD_AGENT is not enabled")

    def _require_research_write_role() -> None:
        fn = getattr(current_user, "can_run_research_writes", None)
        if not callable(fn) or not fn():
            raise ValidationError("当前账号无权执行该研究型写操作（需管理员、开发者或研究员）")

    @bp.post("/rdagent/run")
    @login_required
    def rdagent_run():
        _require()
        _require_research_write_role()
        body = request.get_json(silent=True) or {}
        if not isinstance(body, dict):
            raise ValidationError("JSON object required")
        out = rdagent_run_service.submit_run(body)
        return _wrap(
            {
                "task_id": out["run_id"],
                "progress": out["progress"],
                "status": out["status"],
                "execution_mode": out["execution_mode"],
                "poll_url": f"/api/rdagent/tasks/{out['run_id']}",
                "v1_poll_url": f"/api/v1/rd-agent/runs/{out['run_id']}",
            },
        )

    @bp.get("/rdagent/tasks/<job_id>")
    @login_required
    def rdagent_task_status(job_id: str):
        _require()
        row = rdagent_run_service.get_run(job_id)
        if row is None:
            raise ValidationError("task not found")
        return _wrap(row)

    return bp
