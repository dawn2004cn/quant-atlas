from __future__ import annotations
"""Journey catalog API — user-facing journey listing and route index.

Endpoints:
  GET  /api/v1/journeys            — list all journeys with route counts
  GET  /api/v1/journeys/<name>    — detail for one journey (routes, description)
  GET  /api/v1/journeys/<name>/routes — raw route name list for a journey
"""

from flask import Blueprint
from flask_login import login_required

from app.core.registry import registered_route_names, registered_routes_by_context
from app.core.logger import get_logger

from .common import ok_response
from .journeys import (
    build_journey_context,
    get_journey_metadata,
    get_route_modules_for_journey,
    get_journey_for_route_module,
)
from .v1_context import ApiV1Context

logger = get_logger(__name__)


def _route_entry(name: str) -> dict:
    meta = registered_routes_by_context().get(name, {})
    entry = {"name": name}
    if meta.get("description"):
        entry["description"] = meta["description"]
    if meta.get("context"):
        entry["context"] = meta["context"]
    if meta.get("depends_on"):
        entry["depends_on"] = meta["depends_on"]
    return entry


def register_journey_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/journeys")
    @login_required
    def list_journeys():
        catalog = build_journey_context()
        journeys = catalog["journeys"]
        return ok_response(
            data={"journeys": journeys, "total": len(journeys)},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/journeys/<journey_name>")
    @login_required
    def get_journey_detail(journey_name: str):
        meta = get_journey_metadata(journey_name)
        if meta is None:
            return ok_response(
                data={"error": "journey_not_found", "journey": journey_name},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )

        modules = get_route_modules_for_journey(journey_name)
        all_registered = set(registered_route_names())
        routes = [_route_entry(m) for m in modules if m in all_registered]

        return ok_response(
            data={
                "name": journey_name,
                "label": meta["label"],
                "label_en": meta["label_en"],
                "description": meta["description"],
                "icon": meta["icon"],
                "routes": routes,
                "route_count": len(routes),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/journeys/<journey_name>/routes")
    @login_required
    def list_journey_routes(journey_name: str):
        meta = get_journey_metadata(journey_name)
        if meta is None:
            return ok_response(
                data={"error": "journey_not_found", "journey": journey_name},
                legacy_alias_key=None,
                enable_legacy_alias=legacy,
            )

        modules = get_route_modules_for_journey(journey_name)
        all_registered = set(registered_route_names())
        available = [m for m in modules if m in all_registered]
        missing = [m for m in modules if m not in all_registered]

        return ok_response(
            data={
                "journey": journey_name,
                "available_routes": available,
                "missing_routes": missing,
                "total": len(available),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )
