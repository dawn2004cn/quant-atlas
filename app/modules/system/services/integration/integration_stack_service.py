"""Integration stack status facade: aggregates health of sub-modules, follows LoD.

Lazy-imports heavy services at call-time so the module can be imported
even when dependencies (BotEngine, BaseStrategy, Qlib, Celery) are missing.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from typing import Any

from app.config import AppSettings
from app.core.logger import get_logger
from app.modules.system.services.helpers.integration_probe_access import get_integration_probe_port

logger = get_logger(__name__)


def _json_safe(obj: object) -> Any:
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return obj


class IntegrationStackService:
    """Read-only runtime summary of analysis/data/execution/payment integration modules.

    All heavy service dependencies are passed as constructor kwargs and
    imported lazily inside probe methods.
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        kronos_service: Any | None = None,
        quantml_factor_service: Any | None = None,
        agentic_analysis_service: Any | None = None,
        global_market_service: Any | None = None,
        trading_bot_service: Any | None = None,
        payment_orchestrator: Any | None = None,
        fingpt_application_service: Any | None = None,
    ) -> None:
        self._settings = settings
        self._kronos = kronos_service
        self._quantml = quantml_factor_service
        self._agentic = agentic_analysis_service
        self._global_market = global_market_service
        self._trading = trading_bot_service
        self._payments = payment_orchestrator
        self._fingpt_app = fingpt_application_service

    def get_stack_status(self) -> dict[str, Any]:
        """Return sub-stack availability and light stats; single-module failures don't break the whole structure."""
        mysql = bool(self._settings.use_mysql)

        out: dict[str, Any] = {
            "mysql_enabled": mysql,
            "layers": {},
        }

        out["layers"]["qlib"] = self._probe_qlib()
        out["layers"]["kronos"] = self._probe_kronos()
        out["layers"]["quantml_factors"] = self._probe_quantml()
        out["layers"]["quantml_agent"] = self._probe_agent()
        out["layers"]["fingpt"] = self._probe_fingpt()
        out["layers"]["openbb_global"] = {
            "mysql_cache_expected": mysql,
            **_probe_openbb_light(self._global_market),
        }
        out["layers"]["celery_tasks"] = self._probe_celery()
        out["layers"]["timeseries_ohlcv"] = self._probe_timeseries()
        out["layers"]["execution_gateway"] = self._probe_execution()
        out["layers"]["freqtrade_style_bot"] = {
            "service_ready": self._trading is not None,
            "mysql_tables_expected": mysql,
            "hint": "TradingBotService + ft_trades/ft_orders (MySQL)",
        }
        out["layers"]["hyperswitch_style_payments"] = {
            "orchestrator_ready": self._payments is not None,
            "mysql_tables_expected": mysql,
            "hint": "PaymentOrchestrator + gateway_configs/payment_* (MySQL)",
        }

        if mysql and self._settings.mysql is not None:
            out["mysql_integration_row_counts"] = self._mysql_integration_row_counts()

        return out

    def _probe_celery(self) -> dict[str, Any]:
        try:
            from app.config import get_runtime_bool, get_runtime

            enabled = get_runtime_bool("ENABLE_CELERY", False)
            if not enabled:
                return {"ok": False, "enabled": False, "reason": "ENABLE_CELERY=0 in .env"}

            from ...celery_app import celery

            broker = get_runtime("CELERY_BROKER_URL", "")
            from app.infrastructure.timeseries.sync_snapshot import describe_questdb_sync_beat

            return {
                "ok": True,
                "enabled": True,
                "broker_url_configured": bool(broker),
                "app_name": getattr(celery, "main", "celery"),
                "broker": broker[:50] if broker else "not configured",
                "questdb_beat": describe_questdb_sync_beat(),
            }
        except ImportError:
            return {"ok": False, "reason": "celery not installed or not accessible"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _probe_qlib(self) -> dict[str, Any]:
        try:
            from app.config import get_runtime_bool

            enabled = get_runtime_bool("ENABLE_QLIB", False)
            if not enabled:
                return {"ok": False, "enabled": False, "reason": "ENABLE_QLIB=0 in .env"}

            import qlib

            return {
                "ok": True,
                "enabled": True,
                "qlib_version": getattr(qlib, "__version__", "unknown"),
                "data_path": str(getattr(qlib, "data_path", "not configured")),
            }
        except ImportError:
            return {"ok": False, "reason": "qlib not installed"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _probe_timeseries(self) -> dict[str, Any]:
        try:
            from app.infrastructure.timeseries.timeseries_factory import timeseries_health_probe

            probe = timeseries_health_probe()
            q = probe.get("questdb") or {}
            ohlcv = probe.get("ohlcv_tables") or {}
            last = probe.get("last_sync") or {}
            warnings = probe.get("warnings") or []
            enabled = bool(q.get("enabled"))
            connected = bool(q.get("connected"))
            rows = int(ohlcv.get("questdb_rows") or 0)
            ok = bool(probe.get("ok")) and not warnings
            if not enabled:
                ok = True
            from app.infrastructure.timeseries.sync_snapshot import (
                describe_questdb_sync_beat,
                get_timeseries_sync_history,
            )

            beat = describe_questdb_sync_beat()
            beat_history = get_timeseries_sync_history(limit=20, source="celery_beat")
            return {
                "ok": ok,
                "questdb_enabled": enabled,
                "questdb_connected": connected,
                "questdb_rows": rows,
                "questdb_sample_sh600519": int(ohlcv.get("questdb_sample_sh600519") or 0),
                "clickhouse_rows": int(ohlcv.get("clickhouse_rows") or 0),
                "warnings": warnings,
                "last_sync_at": last.get("recorded_at"),
                "last_sync_ok": last.get("ok"),
                "last_sync_source": last.get("source"),
                "last_sync_rows": last.get("questdb_rows_written"),
                "last_sync_mode": last.get("mode"),
                "last_sync_failed_samples": last.get("failed_samples"),
                "last_sync_skipped": last.get("skipped"),
                "last_sync_reason": last.get("reason"),
                "sync_progress": probe.get("sync_progress"),
                "celery_beat": beat,
                "beat_history_count": len(beat_history),
                "recent_beat_runs": beat.get("recent_beat_runs") or beat_history[:5],
            }
        except Exception as exc:
            logger.warning("integration_stack timeseries probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _probe_execution(self) -> dict[str, Any]:
        try:
            from app.core.runtime_config import get_runtime, get_runtime_bool
            from app.infrastructure.execution.qmt_executor import qmt_executor_status

            qmt = self._settings.qmt
            qmt_status = qmt_executor_status(
                account_id=qmt.account_id or "",
                qmt_path=qmt.qmt_path or "",
            )
            mode = qmt_status.get("execution_mode") or "disabled"
            ok = mode in ("simulation", "live")
            return {
                "ok": ok,
                "default_mode": get_runtime("EXECUTION_DEFAULT_MODE", "paper"),
                "borderless_enabled": get_runtime_bool("BORDERLESS_EXECUTION_ENABLED", True),
                "qmt": qmt_status,
            }
        except Exception as exc:
            logger.warning("integration_stack execution probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _probe_kronos(self) -> dict[str, Any]:
        if self._kronos is None:
            return {"ok": False, "reason": "service not configured"}
        try:
            models = self._kronos.list_models()
            brief = [
                {"model_id": getattr(m, "model_id", str(m)), "model_type": getattr(m, "model_type", "")}
                for m in models[:12]
            ]
            return {"ok": True, "model_count": len(models), "sample": brief}
        except Exception as exc:
            logger.warning("integration_stack kronos probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _probe_quantml(self) -> dict[str, Any]:
        if self._quantml is None:
            return {"ok": False, "reason": "service not configured"}
        try:
            rows = self._quantml.list_factors(category=None, limit=5)
            return {
                "ok": True,
                "sample_count": len(rows),
                "sample_names": [getattr(r, "factor_name", "") for r in rows],
            }
        except Exception as exc:
            logger.warning("integration_stack quantml probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _probe_agent(self) -> dict[str, Any]:
        if self._agentic is None:
            return {"ok": False, "skipped": True, "reason": "agentic_service_not_initialized"}
        try:
            insight = self._agentic.get_latest_market_insight("CN")
            if insight is None:
                return {"ok": True, "has_insight": False}
            d = asdict(insight)
            return {"ok": True, "has_insight": True, "latest": _json_safe(d)}
        except Exception as exc:
            logger.warning("integration_stack agent probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _probe_fingpt(self) -> dict[str, Any]:
        if self._fingpt_app is None:
            return {"ok": False, "skipped": True, "reason": "mysql_disabled_or_no_repository"}
        try:
            return self._fingpt_app.probe_integration_stack_layer()
        except Exception as exc:
            logger.warning("integration_stack fingpt probe failed: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _mysql_integration_row_counts(self) -> dict[str, Any]:
        """Read-only row counts for Freqtrade / Hyperswitch / FinGPT / Kronos / OpenBB tables."""
        ms = self._settings.mysql
        if ms is None or not self._settings.use_mysql:
            return {}
        probe = get_integration_probe_port()
        if probe is None:
            return {}
        tables = (
            ("ft_trades", "ft_trades"),
            ("ft_orders", "ft_orders"),
            ("payment_intents", "payment_intents"),
            ("payment_refunds", "payment_refunds"),
            ("gateway_configs", "gateway_configs"),
            ("fingpt_predictions", "fingpt_predictions"),
            ("fingpt_sentiment", "fingpt_sentiment"),
            ("kronos_predictions", "kronos_predictions"),
            ("kronos_models", "kronos_models"),
            ("openbb_data_cache", "openbb_data_cache"),
            ("quantml_factors", "quantml_factors"),
            ("agent_market_insights", "agent_market_insights"),
        )
        return probe.count_tables(tables)


def _probe_openbb_light(svc: Any) -> dict[str, Any]:
    """Do not initiate external network requests; only confirm service object is available."""
    try:
        _ = svc.get_global_quote
        _ = svc.get_global_history
        return {"adapter_callable": True}
    except Exception as exc:
        return {"adapter_callable": False, "error": str(exc)}
