from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from flask import jsonify

from app.bootstrap_components.service_wiring import _get_registry
from app.core.logger import get_logger
from app.core.mesh.unified_data_lake import DataQuery, DataScope
from app.core.registry import ServiceRegistry, register_routes
from app.modules.data.services.data_lake_manager import DataLakeManager
from app.presentation.api.error_codes import ErrorCode, error_payload
from app.presentation.api.responses import success_response
from app.presentation.api.decorators import require_role

logger = get_logger(__name__)


@register_routes(name="data_lake", context="data", description="Unified Data Lake health and migration")
def register_data_lake_routes(blueprint, ctx):
    """Register routes for Data Lake management and health."""
    del ctx
    registry: ServiceRegistry = _get_registry()

    @blueprint.route("/data-lake/health", methods=["GET"])
    def get_health():
        lake_manager: DataLakeManager = registry.get("data_lake_manager")
        try:
            health = lake_manager.get_system_health()
            return success_response(data=health)
        except Exception as e:
            logger.exception("Failed to fetch data lake health")
            payload = error_payload(ErrorCode.INTERNAL_ERROR, str(e))
            return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status

    @blueprint.route("/data-lake/migrate", methods=["POST"])
    @require_role("can_manage_users")
    def trigger_migration():
        """Trigger full legacy DB migration to the unified data lake."""
        runner = registry.get("data_migration_runner")
        try:
            result = asyncio.run(runner.run_full_migration())
            return success_response(data=result)
        except Exception as e:
            logger.exception("Migration failed")
            payload = error_payload(ErrorCode.INTERNAL_ERROR, str(e))
            return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status

    @blueprint.route("/data-lake/migrate/progress", methods=["GET"])
    def get_migration_progress():
        runner = registry.get("data_migration_runner")
        return success_response(data=runner.get_progress())

    @blueprint.route("/data-lake/verify/<symbol>", methods=["GET"])
    @require_role("can_manage_users")
    def verify_symbol(symbol: str):
        """Check if a specific symbol has been migrated and is healthy."""
        lake_manager: DataLakeManager = registry.get("data_lake_manager")
        try:
            query = DataQuery(
                symbol=symbol,
                market="CN",
                start_date=datetime.now() - timedelta(days=1),
                scope=DataScope.HISTORICAL,
            )
            df, warnings = asyncio.run(lake_manager.get_data(query))
            return success_response(
                data={
                    "symbol": symbol,
                    "exists": not df.empty,
                    "row_count": len(df),
                    "warnings": warnings,
                }
            )
        except Exception as e:
            logger.exception("Verification failed for %s", symbol)
            payload = error_payload(ErrorCode.INTERNAL_ERROR, str(e))
            return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status

    @blueprint.route("/data-lake/stats", methods=["GET"])
    def get_lake_stats():
        """Show lake migration manifest and store health."""
        lake_manager: DataLakeManager = registry.get("data_lake_manager")
        try:
            status = lake_manager.get_lake_status()
            store_health = lake_manager._store.get_health_status()
            return success_response(
                data={
                    "lake": status,
                    "store": store_health,
                    "engine": status.get("engine"),
                    "target": status.get("target_engine"),
                    "migration_pct": status.get("progress_pct", 0),
                }
            )
        except Exception as e:
            logger.exception("Failed to fetch lake stats")
            payload = error_payload(ErrorCode.INTERNAL_ERROR, str(e))
            return jsonify(payload), ErrorCode.INTERNAL_ERROR.http_status
