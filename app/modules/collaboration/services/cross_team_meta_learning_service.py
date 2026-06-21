from __future__ import annotations
"""Cross-team meta-learning — anonymous patterns and swarm consensus alerts."""

import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.core.logger import get_logger
from app.infrastructure.collaboration.cross_team_store import CrossTeamStore

logger = get_logger(__name__)

_MIN_TEAMS_SITE_ALERT = 3
_CONSENSUS_WINDOW_HOURS = 48
_MIN_CONFIDENCE = 0.6
_ALERT_COOLDOWN_HOURS = 6


class CrossTeamMetaLearningService:
    """Aggregate anonymized team arbiter signals into site-wide intelligence."""

    def __init__(
        self,
        *,
        store: CrossTeamStore | None = None,
        secret: str | None = None,
        min_teams: int = _MIN_TEAMS_SITE_ALERT,
        meta_arbiter_service: Any | None = None,
    ) -> None:
        self._store = store or CrossTeamStore()
        if secret:
            self._secret = secret
        else:
            try:
                from app.config import get_settings
                self._secret = get_settings().resolved_cross_team_secret
            except Exception:  # pragma: no cover — fallback for non-Flask contexts
                self._secret = __import__("secrets").token_hex(32)
        self._min_teams = max(2, min_teams)
        self._meta_arbiter = meta_arbiter_service

    def attach_meta_arbiter(self, service: Any) -> None:
        """Late-bind MetaArbiterService (wired after swarm arbiter)."""
        self._meta_arbiter = service

    def register_team_consensus(
        self,
        *,
        team_id: int,
        symbol: str,
        market: str,
        verdict: str,
        confidence: float,
    ) -> dict[str, Any]:
        """Record a team-level verdict and detect multi-team agreement."""
        sym = symbol.strip().lower()
        mkt = market.upper()
        v = verdict.strip().lower()
        if not sym or v not in ("bullish", "bearish", "neutral"):
            return {"ok": False, "status": "invalid_input"}

        row = {
            "team_fp": self._team_fingerprint(team_id),
            "symbol": sym,
            "market": mkt,
            "verdict": v,
            "confidence": round(float(confidence), 3),
            "created_at": datetime.utcnow().isoformat(),
        }
        self._store.append_consensus(row)
        alert = self._maybe_emit_site_alert(sym, mkt, v)
        return {
            "ok": True,
            "registered": True,
            "team_fingerprint": row["team_fp"],
            "site_alert": alert,
        }

    def share_pattern_from_review(
        self,
        *,
        predicted_verdict: str,
        actual_outcome: str,
        market: str = "CN",
        pnl_pct: float | None = None,
    ) -> dict[str, Any]:
        """Anonymously pool success/failure patterns (no symbol or tenant id)."""
        pred = predicted_verdict.strip().lower()
        actual = actual_outcome.strip().lower()
        success = self._is_success_outcome(actual, pnl_pct)
        pattern_key = f"{pred}->{actual}"
        regime = market.upper()

        data = self._store.load_patterns()
        patterns: list[dict[str, Any]] = list(data.get("patterns") or [])
        found = next((p for p in patterns if p.get("pattern_key") == pattern_key), None)
        if found is None:
            found = {
                "pattern_id": f"ap-{uuid.uuid4().hex[:10]}",
                "pattern_key": pattern_key,
                "scenario_type": "arbiter_review",
                "market_regime": regime,
                "success_count": 0,
                "failure_count": 0,
                "sample_size": 0,
            }
            patterns.append(found)
        if success:
            found["success_count"] = int(found.get("success_count") or 0) + 1
        else:
            found["failure_count"] = int(found.get("failure_count") or 0) + 1
        found["sample_size"] = int(found.get("sample_size") or 0) + 1
        found["last_seen_at"] = datetime.utcnow().isoformat()
        self._store.save_patterns({"patterns": patterns[-500:]})
        return {"ok": True, "pattern_key": pattern_key, "anonymized": True}

    def list_site_alerts(self, *, limit: int = 30) -> dict[str, Any]:
        rows = self._store.list_site_alerts(limit=limit)
        return {"ok": True, "alerts": rows, "count": len(rows)}

    def list_anonymous_patterns(self, *, limit: int = 40) -> dict[str, Any]:
        data = self._store.load_patterns()
        patterns = list(data.get("patterns") or [])
        patterns.sort(key=lambda p: int(p.get("sample_size") or 0), reverse=True)
        return {
            "ok": True,
            "patterns": patterns[:limit],
            "count": len(patterns[:limit]),
            "privacy_note": "不含 tenant_id / symbol / user_id",
        }

    def scan_pending_consensus(self) -> dict[str, Any]:
        """Re-scan recent consensus rows and emit any missing site alerts."""
        rows = self._store.list_consensus(limit=1000)
        emitted = 0
        seen: set[str] = set()
        for row in reversed(rows):
            key = f"{row.get('symbol')}:{row.get('market')}:{row.get('verdict')}"
            if key in seen:
                continue
            seen.add(key)
            alert = self._maybe_emit_site_alert(
                str(row.get("symbol") or ""),
                str(row.get("market") or "CN"),
                str(row.get("verdict") or ""),
            )
            if alert and alert.get("created"):
                emitted += 1
        return {"ok": True, "alerts_emitted": emitted}

    def _maybe_emit_site_alert(self, symbol: str, market: str, verdict: str) -> dict[str, Any] | None:
        if not symbol or verdict == "neutral":
            return None
        cutoff = datetime.utcnow() - timedelta(hours=_CONSENSUS_WINDOW_HOURS)
        rows = self._store.list_consensus(limit=800)
        teams: dict[str, float] = {}
        for row in rows:
            if str(row.get("symbol") or "").lower() != symbol:
                continue
            if str(row.get("market") or "").upper() != market:
                continue
            if str(row.get("verdict") or "").lower() != verdict:
                continue
            try:
                ts = datetime.fromisoformat(str(row.get("created_at") or ""))
            except ValueError:
                continue
            if ts < cutoff:
                continue
            conf = float(row.get("confidence") or 0.0)
            if conf < _MIN_CONFIDENCE:
                continue
            fp = str(row.get("team_fp") or "")
            if fp:
                teams[fp] = max(teams.get(fp, 0.0), conf)

        if len(teams) < self._min_teams:
            return None

        if self._recent_alert_exists(symbol, market, verdict):
            return {"created": False, "reason": "cooldown"}

        avg_conf = sum(teams.values()) / len(teams)
        alert_id = f"cta-{uuid.uuid4().hex[:12]}"
        alert = {
            "id": alert_id,
            "level": "warning" if verdict == "bearish" else "info",
            "category": "cross_team_consensus",
            "title": f"全站级异动 · {symbol.upper()}",
            "message": (
                f"{len(teams)} 个独立团队 Arbiter 在 {market} 市场对 {symbol} "
                f"形成一致「{verdict}」共识（均信 {avg_conf:.0%}）"
            ),
            "symbol": symbol,
            "market": market,
            "verdict": verdict,
            "team_count": len(teams),
            "avg_confidence": round(avg_conf, 3),
            "created_at": datetime.utcnow().isoformat(),
        }
        meta_payload = self._activate_meta_arbitration(symbol, market, verdict)
        if meta_payload:
            alert.update(meta_payload)
            if meta_payload.get("meta_rationale"):
                alert["message"] = (
                    f"{alert['message']} · 元仲裁：{meta_payload['meta_rationale'][:120]}"
                )
        self._store.append_site_alert(alert)
        self._publish_realtime_alert(alert)
        logger.info(
            "cross_team site alert symbol=%s verdict=%s teams=%d",
            symbol,
            verdict,
            len(teams),
        )
        return {"created": True, "alert": alert}

    def _activate_meta_arbitration(
        self,
        symbol: str,
        market: str,
        verdict: str,
    ) -> dict[str, Any] | None:
        if self._meta_arbiter is None:
            return None
        try:
            out = self._meta_arbiter.synthesize(
                symbol,
                market,
                verdict_hint=verdict,
                use_llm=False,
            )
            if not out.get("ok"):
                return None
            from app.domain.meta_arbiter_schema import MetaArbiterVerdict

            fields = MetaArbiterVerdict.model_validate(out).to_alert_fields()
            return fields
        except Exception as exc:  # noqa: BLE001
            logger.warning("meta_arbitration activation failed sym=%s: %s", symbol, exc)
            return None

    def _publish_realtime_alert(self, alert: dict[str, Any]) -> None:
        try:
            from app.core.event_bus import CrossTeamSiteAlertEvent, get_event_bus

            get_event_bus().publish(
                CrossTeamSiteAlertEvent(
                    source="CrossTeamMetaLearningService",
                    alert_id=str(alert.get("id") or ""),
                    symbol=str(alert.get("symbol") or ""),
                    market=str(alert.get("market") or "CN"),
                    verdict=str(alert.get("verdict") or ""),
                    team_count=int(alert.get("team_count") or 0),
                    avg_confidence=float(alert.get("avg_confidence") or 0.0),
                    title=str(alert.get("title") or ""),
                    message=str(alert.get("message") or ""),
                    level=str(alert.get("level") or "info"),
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("cross_team realtime publish: %s", exc)

    def _recent_alert_exists(self, symbol: str, market: str, verdict: str) -> bool:
        cutoff = datetime.utcnow() - timedelta(hours=_ALERT_COOLDOWN_HOURS)
        for row in self._store.list_site_alerts(limit=50):
            if str(row.get("symbol") or "").lower() != symbol:
                continue
            if str(row.get("market") or "").upper() != market:
                continue
            if str(row.get("verdict") or "").lower() != verdict:
                continue
            try:
                ts = datetime.fromisoformat(str(row.get("created_at") or ""))
            except ValueError:
                continue
            if ts >= cutoff:
                return True
        return False

    def _team_fingerprint(self, team_id: int) -> str:
        payload = f"team:{team_id}"
        digest = hmac.new(
            self._secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:16]
        return f"tf-{digest}"

    @staticmethod
    def _is_success_outcome(actual: str, pnl_pct: float | None) -> bool:
        if pnl_pct is not None:
            return pnl_pct > 0
        return actual in ("win", "profit", "bullish", "success", "correct")
