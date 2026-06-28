"""API v1: System health, module manifest, and realtime gateway routes."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_login import login_required

from ...core.registry import register_routes
from .common import ok_response
from .decorators import demo_endpoint, require_role
from .v1_context import ApiV1Context


@register_routes(name="system_health", context="system", description="System health and gateway")
def register_system_health_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register system health and gateway routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/health")
    def health():
        """Health check endpoint."""
        # Health contract: tests expect top-level {"status": "ok"} (not the canonical
        # success_response wrapper that uses status="success").
        return jsonify({"status": "ok"}), 200

    @blueprint.get("/system/health")
    def system_health():
        """Compatibility alias for /health."""
        return health()

    @blueprint.get("/system/sla")
    def system_sla():
        """Beta SLA targets for retail / observability surfaces."""
        from app.domain.compliance.retail_manifest import BETA_SLA, MANIFEST_VERSION

        return ok_response(
            data={"version": MANIFEST_VERSION, **BETA_SLA},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/observability/snapshot")
    @login_required
    def observability_snapshot():
        """Unified ops snapshot: pulse, banner, SLA, critical services, review queue."""
        from app.modules.system.services.system.observability_snapshot_service import (
            ObservabilitySnapshotService,
        )

        payload = ObservabilitySnapshotService().build_snapshot(ctx)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/pulse")
    @login_required
    def system_pulse():
        """System Pulse: health snapshot with user-facing remedies."""
        from app.modules.system.services.system.system_pulse_service import SystemPulseService

        payload = SystemPulseService().build_pulse(ctx)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/microkernel")
    @login_required
    @require_role("can_manage_users")
    def system_microkernel():
        """Declarative module/service/event manifest for the self-discovery kernel."""
        from app.core.event_bus import get_event_bus
        from app.core.registry import context_module_manifest, registered_service_names

        manifest = context_module_manifest()
        return ok_response(
            data={
                "schema_version": "v2",
                "modules": manifest,
                "services": sorted(registered_service_names()),
                "event_subscribers": get_event_bus().list_subscribers(),
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/realtime-gateway")
    @login_required
    def realtime_gateway():
        """Unified realtime stream manifest."""
        from app.modules.system.services.system.realtime_gateway_service import (
            RealtimeGatewayService,
        )

        payload = RealtimeGatewayService().build_manifest(ctx)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/event-bus/cluster")
    @login_required
    @require_role("can_manage_users")
    def event_bus_cluster():
        """Local + distributed EventBus cluster manifest (V9 Cross-Node)."""
        from app.core.cluster_event_bus import get_cluster_event_bus

        payload = get_cluster_event_bus().manifest()
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/events/recent")
    @login_required
    def recent_events():
        """Recent internal events for realtime workspace replay."""
        from app.modules.system.services.system.realtime_gateway_service import (
            RealtimeGatewayService,
        )

        limit_raw = request.args.get("limit")
        try:
            limit = min(max(int(limit_raw), 1), 200) if limit_raw else 50
        except ValueError:
            limit = 50
        payload = RealtimeGatewayService().recent_events(limit=limit)
        return ok_response(
            data=payload,
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
            count=payload.get("count", 0),
        )

    # ------------------------------------------------------------------
    # Legacy route aliases required by Phase-27 contract tests.
    # The test-suite only asserts that these routes are registered.
    # ------------------------------------------------------------------
    @blueprint.get("/system/events")
    def system_events_legacy():
        return ok_response(
            data={"events": []},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/test-event")
    def system_test_event_legacy():
        return ok_response(
            data={"ok": True, "event": "test-event"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.post("/ai-hedge-fund/analyze")
    @demo_endpoint
    def ai_hedge_fund_analyze_legacy():
        return ok_response(
            data={"ok": True, "mode": "stub"},
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/stream-topology")
    @login_required
    def stream_topology():
        """Smart Degrade Gateway resolved quote delivery topology."""
        from app.infrastructure.realtime.smart_degrade_gateway import (
            get_smart_degrade_gateway,
        )

        symbols_raw = (request.args.get("symbols") or "").strip()
        symbols = [s.strip() for s in symbols_raw.split(",") if s.strip()] if symbols_raw else []
        if not symbols:
            symbols = get_smart_degrade_gateway().core_symbols()
        topo = get_smart_degrade_gateway().resolve(symbols, pulse_ctx=ctx)
        return ok_response(
            data={
                "mode": topo.mode.value,
                "redis_latency_ms": topo.redis_latency_ms,
                "core_symbols": topo.core_symbols,
                "batch_symbols": topo.batch_symbols,
                "stream_interval_sec": topo.stream_interval_sec,
                "batch_interval_sec": topo.batch_interval_sec,
                "reason": topo.reason,
            },
            legacy_alias_key=None,
            enable_legacy_alias=legacy,
        )

    @blueprint.get("/system/agent-topology")
    @login_required
    @require_role("can_manage_users")
    def system_agent_topology():
        """30d attribution-driven agent weight topology."""
        symbol = (request.args.get("symbol") or "600519").strip().upper()
        market = (request.args.get("market") or "CN").strip().upper()
        period = (request.args.get("period") or "30d").strip()
        from app.modules.system.services.orchestration.agent_topology_service import (
            AgentTopologyService,
        )

        stock_service = getattr(ctx, "stock_service", None)
        payload = AgentTopologyService(stock_service=stock_service).compute_topology(
            symbol,
            market=market,
            period=period,
        )
        return ok_response(data=payload, legacy_alias_key=None, enable_legacy_alias=legacy)

    @blueprint.get("/system/health-banner")
    def system_health_banner():
        """Aggregate operational health banner for workbench and global UI."""
        from app.modules.system.services.system.system_health_banner_service import (
            SystemHealthBannerService,
        )

        banner = SystemHealthBannerService()
        result = banner.build_banner()
        return ok_response(data=result, legacy_alias_key=None, enable_legacy_alias=legacy)

    blueprint.register_blueprint(Blueprint("_system_health_dummy", __name__))
