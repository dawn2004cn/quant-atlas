"""Tournament audit / last-run API (DIF P2 light dashboard data)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flask import Blueprint, request

from app.core.registry import register_routes
from app.presentation.api.responses import error_response, success_response


def _latest_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    return root / "instance" / "tournament_runs" / "latest.json"


def _summarize(payload: dict[str, Any]) -> dict[str, Any]:
    verdicts = payload.get("verdicts") or []
    if not isinstance(verdicts, list):
        verdicts = []
    accepted_rows = [v for v in verdicts if isinstance(v, dict) and v.get("accepted")]
    rejected_rows = [v for v in verdicts if isinstance(v, dict) and not v.get("accepted")]
    return {
        **payload,
        "summary": {
            "accepted": int(payload.get("accepted") or len(accepted_rows)),
            "rejected": int(payload.get("rejected") or len(rejected_rows)),
            "skipped": int(payload.get("skipped") or 0),
            "loaded": int(payload.get("loaded") or 0),
            "ts": payload.get("ts"),
        },
        "accepted_rows": accepted_rows[:50],
        "rejected_rows": rejected_rows[:50],
    }


@register_routes(name="strategy_tournament", context="strategy", description="Strategy tournament audit")
def register_strategy_tournament_routes(blueprint, ctx=None) -> None:
    _ = ctx
    bp = Blueprint("strategy_tournament", __name__, url_prefix="/strategy/tournament")

    @bp.get("/last-run")
    def tournament_last_run():
        path = _latest_path()
        if not path.exists():
            return error_response("tournament_run_not_found", code=404)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return error_response(f"tournament_run_corrupt:{exc}", code=500)
        if not isinstance(data, dict):
            return error_response("tournament_run_invalid", code=500)
        return success_response(_summarize(data))

    @bp.post("/run")
    def tournament_run_now():
        """Ops: run offline tournament tick synchronously and return audit summary."""
        limit = 200
        body = request.get_json(silent=True) or {}
        if isinstance(body, dict) and body.get("limit") is not None:
            try:
                limit = max(1, min(int(body["limit"]), 500))
            except (TypeError, ValueError):
                limit = 200
        from app.tasks.strategy_tournament_tasks import run_strategy_tournament_tick

        result = run_strategy_tournament_tick(limit=limit)
        return success_response(_summarize(result if isinstance(result, dict) else {"ok": False}))

    blueprint.register_blueprint(bp)
