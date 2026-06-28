from __future__ import annotations
"""Data Truth Guardian -- proactive reconciliation and self-heal orchestration."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.event_bus import (
    TruthDeviationEvent,
    get_event_bus,
)
from app.core.logger import get_logger

logger = get_logger(__name__)
from app.core.mesh.distributed_event_bus import get_distributed_event_bus
from app.core.runtime_config import get_runtime_bool
from app.domain.data_truth.byzantine_consensus import QuorumConsensusResult
from app.domain.data_truth.guardian_schema import (
    DataHealAction,
    GuardianManifest,
    GuardianQuorumRequest,
    GuardianScanRequest,
)
from app.domain.verification import list_pending
from app.infrastructure.realtime.truth_sentry import TruthSentry

logger = get_logger(__name__)

_QLIB_SYNC_TASK = "app.tasks.qlib_data_update.mysql_to_qlib_incremental_sync"


class DataTruthGuardianService:
    """Extend TruthSentry with batch scan, heal plans, and audit trail."""

    def __init__(
        self,
        *,
        data_quality: Any | None = None,
        truth_sentry: TruthSentry | None = None,
        task_dispatcher: Any | None = None,
        store_path: str | Path | None = None,
        blackboard_service: Any | None = None,
    ) -> None:
        self._quality = data_quality
        self._sentry = truth_sentry or (TruthSentry(data_quality) if data_quality else None)
        self._dispatcher = task_dispatcher
        self._blackboard_service = blackboard_service
        root = Path(__file__).resolve().parents[4]
        default_store = root / "instance" / "data_truth" / "heal_log.jsonl"
        self._store_path = Path(store_path) if store_path else default_store
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        self._auto_heal_started = False

    def set_blackboard_service(self, service: Any | None) -> None:
        self._blackboard_service = service

    def start_auto_heal(self) -> None:
        """Subscribe to TruthDeviationEvent and auto-dispatch backfill tasks."""
        if self._auto_heal_started:
            return
        bus = get_event_bus()
        bus.subscribe(TruthDeviationEvent, self._on_deviation_auto_heal, priority=40)
        self._auto_heal_started = True
        logger.info("DataTruthGuardian auto-heal started")

    def _on_deviation_auto_heal(self, event: TruthDeviationEvent) -> None:
        """Auto-heal handler: plan and dispatch backfill task on deviation."""
        symbol = (event.symbol or "").strip().upper()
        market = (event.market or "CN").strip().upper()
        if not symbol:
            return

        # Publish anomaly to blackboard
        self.publish_anomaly_to_blackboard(
            symbol=symbol,
            anomaly_type="data_deviation",
            narrative=f"Auto-detected data deviation for {symbol} ({market}): {event.diff_pct:.2f}% diff",
            payload={
                "event_type": "auto_heal",
                "symbol": symbol,
                "market": market,
                "diff_pct": event.diff_pct,
                "threshold_pct": event.threshold_pct,
                "source_a": event.source_a,
                "source_b": event.source_b,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        action = self._plan_heal(symbol, market, event)
        result = self._execute_heal(action)
        status = "dispatched" if result.dispatched else "skipped"
        self._notify_self_heal(
            {
                "type": "auto_heal",
                "symbol": symbol,
                "market": market,
                "action": result.action,
                "status": status,
                "task_name": result.task_name,
                "evidence": result.evidence,
            }
        )
        if result.dispatched:
            logger.info(
                "auto-heal dispatched %s for %s (%s): task=%s",
                result.action, symbol, market, result.task_name,
            )
        else:
            logger.warning("auto-heal skipped for %s: no dispatcher", symbol)

    def get_manifest(self) -> dict[str, Any]:
        threshold = getattr(self._sentry, "_threshold", 0.5) if self._sentry else 0.5
        manifest = GuardianManifest(
            enabled=get_runtime_bool("DATA_TRUTH_GUARDIAN_ENABLED", True),
            diff_threshold_pct=float(threshold),
            sources=["TDX", "Qlib", "AkShare"],
            heal_actions=["acknowledge", "resync_qlib", "rescan", "clear_pending"],
            mesh_linked=get_distributed_event_bus() is not None,
            quorum_enabled=get_runtime_bool("DATA_TRUTH_QUORUM_ENABLED", True),
        )
        pending = list_pending()
        return {
            "ok": True,
            **manifest.model_dump(mode="json"),
            "pending_count": len(pending),
        }

    def get_source_health(self, source: str) -> dict[str, Any]:
        """Return confidence score for a given data source.

        Returns a dict with 'confidence' (0..1), 'staleness_days', and 'last_valid'.
        """
        if self._sentry:
            health = self._sentry.get_source_health(source)
            if health:
                return health
        # Fallback: return a stub confidence score
        return {"confidence": 0.85, "staleness_days": 0, "last_valid": "unknown"}

    def list_pending(self) -> dict[str, Any]:
        pending = list_pending()
        return {"ok": True, "pending": pending, "count": len(pending)}

    def quorum_scan(self, request: GuardianQuorumRequest) -> dict[str, Any]:
        """Byzantine quorum scan across TDX / Qlib / AkShare closes."""
        if self._quality is None or not hasattr(self._quality, "quorum_consensus"):
            return {"ok": False, "error": "quorum_unavailable"}
        symbols = [s.strip().upper() for s in request.symbols if (s or "").strip()]
        if not symbols:
            return {"ok": False, "error": "symbols_required"}

        market = (request.market or "CN").strip().upper()
        results: list[dict[str, Any]] = []
        faults = 0
        for sym in symbols:
            result: QuorumConsensusResult = self._quality.quorum_consensus(sym, market)
            row = {
                "symbol": sym,
                "market": market,
                "consensus_value": result.consensus_value,
                "source_deviations": result.source_deviations,
                "outlier_sources": result.outlier_sources,
                "quorum_median": result.consensus_value,
                "is_consensus": not result.byzantine_fault,
                "confidence": result.confidence,
            }

            # Publish anomaly to blackboard if consensus failed
            if not (not result.byzantine_fault) and result.outlier_sources:
                self.publish_anomaly_to_blackboard(
                    symbol=sym,
                    anomaly_type="quorum_failure",
                    narrative=f"Quorum consensus failed for {sym}: outliers={result.outlier_sources}",
                    payload={
                        "event_type": "quorum_scan",
                        "symbol": sym,
                        "market": market,
                        "outlier_sources": result.outlier_sources,
                        "confidence": result.confidence,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                )

            results.append(row)
            if not (not result.byzantine_fault):
                faults += 1

        return {
            "ok": True,
            "symbols": symbols,
            "market": market,
            "results": results,
            "quorum_results": results,
            "byzantine_fault_count": faults,
            "consensus_rate": round((len(symbols) - faults) / len(symbols), 3),
        }

    def scan(self, request: GuardianScanRequest) -> dict[str, Any]:
        """Batch scan multiple symbols for data truth."""
        symbols = [s.strip().upper() for s in request.symbols if (s or "").strip()]
        if not symbols:
            return {"ok": False, "error": "symbols_required"}

        market = (request.market or "CN").strip().upper()
        results: list[dict[str, Any]] = []
        deviations: list[dict[str, Any]] = []

        has_scan = self._sentry and hasattr(self._sentry, "scan")

        if has_scan:
            for sym in symbols:
                scan_result = self._sentry.scan(sym, market)
                results.append(scan_result)
                if scan_result.get("issues") or scan_result.get("warnings"):
                    self.publish_anomaly_to_blackboard(
                        symbol=sym,
                        anomaly_type="data_scan",
                        narrative=f"Data scan completed for {sym}: {len(scan_result.get('issues', []))} issues, {len(scan_result.get('warnings', []))} warnings",
                        payload={
                            "event_type": "data_scan",
                            "symbol": sym,
                            "market": market,
                            "issues": scan_result.get("issues", []),
                            "warnings": scan_result.get("warnings", []),
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    deviations.extend(scan_result.get("issues", []))
                    deviations.extend(scan_result.get("warnings", []))
        elif self._quality:
            for sym in symbols:
                comps = self._quality.compare_sources(sym, market)
                sym_results: list[dict[str, Any]] = []
                for comp in comps:
                    row: dict[str, Any] = {
                        "symbol": sym,
                        "market": market,
                        "field": comp.field,
                        "source_a": comp.source_a,
                        "source_b": comp.source_b,
                        "value_a": comp.value_a,
                        "value_b": comp.value_b,
                        "diff_pct": comp.diff_pct,
                        "anomaly": comp.anomaly,
                    }
                    sym_results.append(row)
                    if comp.anomaly:
                        deviations.append(row)
                        self.publish_anomaly_to_blackboard(
                            symbol=sym,
                            anomaly_type="data_scan",
                            narrative=f"Deviation detected: {comp.source_a} vs {comp.source_b} on {comp.field}: {comp.diff_pct:.2f}%",
                            payload={
                                "event_type": "data_scan",
                                "symbol": sym,
                                "market": market,
                                "field": comp.field,
                                "diff_pct": comp.diff_pct,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                results.extend(sym_results)

        return {
            "ok": True,
            "symbols": symbols,
            "market": market,
            "results": results,
            "deviation_count": len(deviations),
            "deviations": deviations,
        }

    def heal(self, symbol: str, market: str = "CN", action: str = "resync_qlib") -> dict[str, Any]:
        """Manually trigger a heal action for a symbol."""
        symbol = symbol.strip().upper()
        market = market.strip().upper()

        # Publish heal action to blackboard
        self.publish_anomaly_to_blackboard(
            symbol=symbol,
            anomaly_type="manual_heal",
            narrative=f"Manual heal triggered for {symbol} ({market}): action={action}",
            payload={
                "event_type": "manual_heal",
                "symbol": symbol,
                "market": market,
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        has_heal = self._sentry and hasattr(self._sentry, "heal")
        if has_heal:
            result = self._sentry.heal(symbol, market, action)
            return {"ok": True, "result": result}

        if self._dispatcher:
            task_name = _QLIB_SYNC_TASK if action == "resync_qlib" else f"heal_{action}"
            try:
                task_id = self._dispatcher.dispatch(task_name, {"symbol": symbol, "market": market})
                return {
                    "ok": True,
                    "action": {"dispatched": True, "task_id": task_id},
                }
            except Exception:  # noqa: BLE001
                logger.warning("Suppressed exception in heal", exc_info=True)
                pass

        return {"ok": True, "action": {"dispatched": False, "reason": "no_dispatcher"}}

    def _plan_heal(self, symbol: str, market: str, event: TruthDeviationEvent) -> DataHealAction:
        """Plan a heal action based on the deviation event."""
        symbol = symbol.strip().upper()
        market = market.strip().upper()

        # Publish heal plan to blackboard
        self.publish_anomaly_to_blackboard(
            symbol=symbol,
            anomaly_type="heal_plan",
            narrative=f"Heal planned for {symbol} ({market}): action={event.action}",
            payload={
                "event_type": "heal_plan",
                "symbol": symbol,
                "market": market,
                "action": event.action,
                "diff_pct": event.diff_pct,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        if event.action == "resync_qlib":
            return DataHealAction(
                action="resync_qlib",
                symbol=symbol,
                market=market,
                task_name=_QLIB_SYNC_TASK,
                evidence={"symbol": symbol, "market": market},
            )
        elif event.action == "rescan":
            return DataHealAction(
                action="rescan",
                symbol=symbol,
                market=market,
                task_name="data_quality_rescan",
                evidence={"symbol": symbol, "market": market},
            )
        else:
            return DataHealAction(
                action="acknowledge",
                symbol=symbol,
                market=market,
                task_name="manual_acknowledge",
                evidence={"symbol": symbol, "market": market},
            )

    def _execute_heal(self, action: DataHealAction) -> DataHealAction:
        """Execute a heal action using the task dispatcher."""
        if self._dispatcher is None:
            return action._replace(dispatched=False, evidence={"error": "dispatcher_unavailable"})

        try:
            task_id = self._dispatcher.dispatch(action.task_name, action.evidence)
            return action._replace(
                dispatched=True,
                task_id=task_id,
                evidence={**action.evidence, "task_id": task_id},
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("heal dispatch failed: %s", exc)
            return action._replace(
                dispatched=False,
                evidence={**action.evidence, "error": str(exc)},
            )

    def _notify_self_heal(self, payload: dict[str, Any]) -> int:
        """Broadcast self-heal event to system alerts room via WebSocket."""
        try:
            from app.infrastructure.realtime.websocket_adapter import broadcast_to_room

            payload["timestamp"] = datetime.now(timezone.utc).isoformat()
            return broadcast_to_room("alerts", "system_self_heal", payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("self-heal notify skipped (no socketio): %s", exc)
        return 0

    def _append_log(self, action: DataHealAction) -> None:
        row = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **action.model_dump(mode="json"),
        }
        try:
            with self._store_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as exc:  # noqa: BLE001
            logger.warning("guardian heal log: %s", exc)

    def list_heal_log(self, *, limit: int = 30) -> dict[str, Any]:
        if not self._store_path.exists():
            return {"ok": True, "actions": [], "count": 0}
        rows: list[dict[str, Any]] = []
        try:
            for line in self._store_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        except Exception as exc:  # noqa: BLE001
            logger.warning("guardian heal log read: %s", exc)
            return {"ok": False, "error": str(exc)}
        rows.reverse()
        lim = min(max(1, limit), 100)
        return {"ok": True, "actions": rows[:lim], "count": len(rows[:lim])}

    def publish_anomaly_to_blackboard(
        self,
        *,
        team_id: int = 0,
        symbol: str = "",
        anomaly_type: str = "data_deviation",
        narrative: str = "",
        payload: dict | None = None,
    ) -> dict[str, Any]:
        """Publish a data anomaly alert to the collaboration blackboard.

        This allows the Guardian to operate as an active Agent, posting
        evidence notes that other agents and team members can see and
        debate in the CollaborationBlackboard.
        """
        if self._blackboard_service is None:
            return {"ok": False, "error": "blackboard_unavailable"}
        try:
            entry = self._blackboard_service.submit_note(
                team_id=team_id,
                user_id=0,
                evidence_key=f"data_truth_guardian.{anomaly_type}",
                evidence_value=narrative[:500] if narrative else anomaly_type,
                agent_role="data_truth_guardian",
                symbol=symbol or None,
                strength="strong",
                narrative=narrative or f"Data anomaly detected: {anomaly_type}",
                payload=payload or {},
            )
            logger.info("Guardian posted anomaly to blackboard: %s", anomaly_type)
            return {"ok": True, "entry": entry}
        except Exception as exc:
            logger.warning("Guardian blackboard publish failed: %s", exc)
            return {"ok": False, "error": str(exc)}
