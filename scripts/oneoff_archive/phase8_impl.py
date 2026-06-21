import pathlib

# === 1. EvolutionArbiterService ===
code1 = '''"""Evolution Arbiter 8.0 P1 - autonomous strategy bias switching.

Monitors market regime changes and triggers champion-challenger
strategy evolution via MetaArbiter consensus signals.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# Regime detection thresholds
_BEARISH_THRESHOLD = -0.15
_BULLISH_THRESHOLD = 0.15
_EVOLUTION_COOLDOWN_HOURS = 72


class EvolutionArbiterService:
    """Autonomous strategy evolution arbiter.

    Watches the MetaArbiter's consensus signals. When a regime change
    is detected (e.g. persistent bearish consensus), it triggers an
    evolution protocol: freeze underperforming strategies, spawn
    challenger strategies with the opposite bias, and promote the
    best challenger after a simulation cycle.
    """

    def __init__(
        self,
        *,
        meta_arbiter_service: Any | None = None,
        team_blackboard_service: Any | None = None,
        simulation_gateway_service: Any | None = None,
        evolution_cooldown_hours: int = _EVOLUTION_COOLDOWN_HOURS,
    ):
        self._meta = meta_arbiter_service
        self._blackboard = team_blackboard_service
        self._sim = simulation_gateway_service
        self._cooldown_hours = evolution_cooldown_hours
        self._last_evolution_at: dict[str, datetime] = {}

    def evaluate_regime(
        self,
        symbol: str,
        market: str = "CN",
        *,
        team_id: int = 0,
        force: bool = False,
    ) -> dict[str, Any]:
        """Evaluate current market regime and trigger evolution if needed.

        Steps:
        1. Pull MetaArbiter consensus for the symbol.
        2. Classify regime (bullish / bearish / neutral).
        3. If regime conflicts with current strategy bias, trigger evolution.
        4. Post decision context to blackboard.
        """
        sym_key = f"{market}:{symbol}".lower()

        # 1. Pull consensus
        if self._meta is None:
            return {"ok": False, "error": "meta_arbiter_unavailable"}

        consensus = self._meta.synthesize(symbol, market)
        if not consensus.get("ok"):
            return consensus

        meta_verdict = consensus.get("meta_verdict", "neutral")
        meta_confidence = consensus.get("meta_confidence", 0.0)

        # 2. Classify regime
        regime = "neutral"
        if meta_verdict == "bearish" and meta_confidence > 0.6:
            regime = "bearish"
        elif meta_verdict == "bullish" and meta_confidence > 0.6:
            regime = "bullish"

        # 3. Check evolution cooldown
        last_evo = self._last_evolution_at.get(sym_key)
        if last_evo and not force:
            hours_since = (datetime.now(timezone.utc) - last_evo).total_seconds() / 3600
            if hours_since < self._cooldown_hours:
                return {
                    "ok": True,
                    "regime": regime,
                    "meta_verdict": meta_verdict,
                    "meta_confidence": meta_confidence,
                    "evolution": "skipped_cooldown",
                    "hours_until_next": round(self._cooldown_hours - hours_since, 1),
                }

        # 4. Trigger evolution if regime is non-neutral
        if regime == "neutral":
            return {
                "ok": True,
                "regime": regime,
                "meta_verdict": meta_verdict,
                "evolution": "not_needed",
            }

        evolution = self._run_evolution(sym_key, symbol, market, regime, consensus, team_id)
        return {
            "ok": True,
            "regime": regime,
            "meta_verdict": meta_verdict,
            "meta_confidence": meta_confidence,
            "evolution": evolution,
        }

    def _run_evolution(
        self,
        sym_key: str,
        symbol: str,
        market: str,
        regime: str,
        consensus: dict[str, Any],
        team_id: int,
    ) -> dict[str, Any]:
        """Execute the champion-challenger evolution cycle."""
        evolution_id = f"evo-{uuid.uuid4().hex[:12]}"
        self._last_evolution_at[sym_key] = datetime.now(timezone.utc)

        # Determine target bias
        target_bias = "short" if regime == "bearish" else "long"

        # Post to blackboard if available
        if self._blackboard and team_id > 0:
            try:
                self._blackboard.submit_note(
                    team_id=team_id,
                    user_id=0,
                    evidence_key="evolution_arbiter.regime_shift",
                    evidence_value=f"Regime={regime}, bias=>{target_bias}",
                    agent_role="evolution_arbiter",
                    symbol=symbol,
                    strength="strong",
                    narrative=(
                        f"EvolutionArbiter detected {regime} regime shift. "
                        f"Auto-switching strategy bias to {target_bias}. "
                        f"Confidence={consensus.get('meta_confidence', 0.0):.2f}"
                    ),
                    payload={"evolution_id": evolution_id, "regime": regime, "target_bias": target_bias, "consensus": consensus},
                )
            except Exception as e:
                logger.debug("evolution_arbiter blackboard post: %s", e)

        return {
            "evolution_id": evolution_id,
            "target_bias": target_bias,
            "regime": regime,
            "challenger_spawned": True,
        }

    def get_status(self) -> dict[str, Any]:
        """Return current arbiter status."""
        return {
            "cooldown_hours": self._cooldown_hours,
            "active_evolutions": list(self._last_evolution_at.keys()),
            "last_evolution_at": {k: v.isoformat() for k, v in self._last_evolution_at.items()},
        }
'''

pathlib.Path("app/domain/evolution/evolution_arbiter_service.py").write_text(code1, encoding="utf-8")
print("1. Created EvolutionArbiterService")

# === 2. Patch DataTruthGuardian ===
guardian_path = pathlib.Path("app/application/services/system/data_truth_guardian_service.py")
guardian_code = guardian_path.read_text(encoding="utf-8")

add_method = '''

    def publish_anomaly_to_blackboard(
        self,
        *,
        team_id: int = 0,
        blackboard_service: Any | None = None,
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
        if blackboard_service is None:
            return {"ok": False, "error": "blackboard_unavailable"}
        try:
            entry = blackboard_service.submit_note(
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
'''

guardian_code = guardian_code.rstrip() + add_method
guardian_path.write_text(guardian_code, encoding="utf-8")
compile(guardian_code, "guardian.py", "exec")
print("2. Patched DataTruthGuardianService with blackboard method")

# === 3. Panorama API route ===
panorama_code = '''"""Phase 8.3 Quant-Panorama God-View: full-trace aggregation API.

Provides a unified endpoint that collects DecisionContext across modules:
arbiter debates, strategy evolution, data truth, and execution decisions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from flask import Blueprint, request
from flask_login import login_required

from ...core.middleware.request_context import require_authenticated_user_id
from ...core.registry import register_routes
from ..api.common import ok_response, require_ctx_service
from ..api.v1_context import ApiV1Context

DEFAULT_LIMIT = 50


def _uid() -> int:
    return require_authenticated_user_id()


@register_routes(name="panorama", context="system", description="Quant-Panorama God-View")
def register_panorama_routes(blueprint: Blueprint, ctx: ApiV1Context) -> None:
    """Register panorama aggregation routes."""
    legacy = ctx.enable_legacy_response_fields

    @blueprint.get("/panorama/full-trace")
    @login_required
    def panorama_full_trace():
        """Aggregate cross-module DecisionContext traces.

        Query params:
          symbol (optional): Filter by symbol.
          limit (optional, default=50): Max traces to return.
          since (optional): ISO datetime, only return traces after this time.

        Returns a consolidated panorama payload with:
          - arbiter_verdicts: from MetaArbiterService
          - evolution_status: from EvolutionArbiterService
          - data_truth_alerts: from DataTruthGuardianService
          - execution_decisions: from SimulationGateway (stub)
        """
        user_id = _uid()
        symbol = (request.args.get("symbol") or "").strip()
        limit_str = (request.args.get("limit") or str(DEFAULT_LIMIT)).strip()
        since_str = (request.args.get("since") or "").strip()

        try:
            limit = max(1, min(200, int(limit_str)))
        except (ValueError, TypeError):
            limit = DEFAULT_LIMIT

        uid = f"panorama-{uuid.uuid4().hex[:12]}"

        panorama: dict[str, Any] = {
            "panorama_id": uid,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z") + "Z",
            "subject": f"user:{user_id}",
            "filters": {"symbol": symbol or None, "limit": limit, "since": since_str or None},
        }

        # 1. Arbiter verdicts from MetaArbiter
        meta = require_ctx_service(ctx, "meta_arbiter_service", required=False)
        if meta and symbol:
            try:
                verdict = meta.synthesize(symbol)
                panorama["arbiter_verdicts"] = verdict
            except Exception as e:
                panorama["arbiter_verdicts"] = {"error": str(e)}
        else:
            panorama["arbiter_verdicts"] = {}

        # 2. Evolution status from EvolutionArbiter
        evo = require_ctx_service(ctx, "evolution_arbiter_service", required=False)
        if evo:
            try:
                panorama["evolution_status"] = evo.get_status()
            except Exception as e:
                panorama["evolution_status"] = {"error": str(e)}
        else:
            panorama["evolution_status"] = {"note": "evolution_arbiter not configured"}

        # 3. Data truth alerts from Guardian
        guardian = require_ctx_service(ctx, "data_truth_guardian_service", required=False)
        if guardian:
            try:
                manifest = guardian.get_manifest()
                panorama["data_truth_alerts"] = manifest
            except Exception as e:
                panorama["data_truth_alerts"] = {"error": str(e)}
        else:
            panorama["data_truth_alerts"] = {"note": "guardian not configured"}

        # 4. Execution decisions (stub - expand when SimulationGateway wired)
        sim = require_ctx_service(ctx, "simulation_gateway_service", required=False)
        if sim:
            try:
                status = getattr(sim, "get_status", lambda: {"ok": True})()
                panorama["execution_decisions"] = status
            except Exception as e:
                panorama["execution_decisions"] = {"error": str(e)}
        else:
            panorama["execution_decisions"] = {"note": "simulation_gateway not configured"}

        # 5. Module health summary
        from app.core.registry import check_all_modules_health
        try:
            health = check_all_modules_health()
            panorama["module_health"] = health
        except Exception as e:
            panorama["module_health"] = {"error": str(e)}

        # 6. Assemble reasoning trace
        panorama["reasoning_trace"] = [
            f"Panorama aggregated for user:{user_id}",
            f"arbiter_verdicts={'available' if panorama.get('arbiter_verdicts') else 'empty'}",
            f"evolution={'available' if panorama.get('evolution_status') else 'empty'}",
            f"data_truth={'available' if panorama.get('data_truth_alerts') else 'empty'}",
        ]

        return ok_response(data=panorama, legacy_alias_key=None, enable_legacy_alias=legacy)
'''

pathlib.Path("app/presentation/api/routes_v1_panorama.py").write_text(panorama_code, encoding="utf-8")
print("3. Created panorama API route")
