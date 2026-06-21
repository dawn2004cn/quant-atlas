"""Complexity budget audit and wiring validation routes."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_login import login_required

from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response
from app.presentation.api.v1.optimization.runtime import get_complexity_budget_service
from app.presentation.api.v1_context import ApiV1Context


def register_optimization_budget_routes(
    blueprint: Blueprint,
    ctx: ApiV1Context,
) -> None:
    _ = ctx

    @blueprint.post("/budget/audit")
    @login_required
    def budget_audit():
        svc = get_complexity_budget_service()
        report = svc.run_audit()
        return success_response(data=report.__dict__)

    @blueprint.get("/budget/report")
    @login_required
    def budget_report():
        svc = get_complexity_budget_service()
        report = svc.get_report()
        if report:
            return success_response(data=report.__dict__)
        payload = error_payload(ErrorCode.NOT_FOUND, "No report yet. Run audit first.")
        return jsonify(payload), ErrorCode.NOT_FOUND.http_status

    @blueprint.get("/budget/dependency-graph")
    @login_required
    def budget_dependency_graph():
        svc = get_complexity_budget_service()
        graph = svc.generate_dependency_graph()
        return success_response(data=graph)

    @blueprint.get("/budget/validate-wiring")
    @login_required
    def budget_validate_wiring():
        svc = get_complexity_budget_service()
        result = svc.validate_wiring()
        return success_response(data=result)
