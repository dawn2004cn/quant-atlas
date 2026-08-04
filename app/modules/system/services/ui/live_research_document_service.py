from __future__ import annotations

"""Live-Document — unified streaming research dashboard payload."""

from datetime import datetime
from typing import Any

from app.agents.research.debate_bus import get_recent_debate_rounds
from app.core.event_bus import get_event_bus
from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.shared.symbol_normalizer import SymbolNormalizer
from app.domain.verification import get_pending_reason, get_verification_status

logger = get_logger(__name__)


class LiveResearchDocumentService:
    """Aggregate truth / resonance / debate / copilot into one live document."""

    def build_document(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        *,
        stock_service: Any | None = None,
        strategy_copilot_service: Any | None = None,
        sequence_chain_service: Any | None = None,
        include_handover: bool = False,
    ) -> dict[str, Any]:
        clean = SymbolNormalizer.to_db_code(symbol)
        mkt = market.value
        lights = self._build_traffic_lights(clean, mkt, stock_service)
        resonance = self._resonance_summary(clean, market, stock_service)
        debate = self._debate_section(clean, mkt)
        events = self._recent_symbol_events(clean, mkt)
        provenance_id = None
        if sequence_chain_service is not None:
            provenance_id = sequence_chain_service.get_active_provenance(clean, mkt)

        handover = None
        if include_handover and strategy_copilot_service is not None:
            try:
                eval_out = strategy_copilot_service.evaluate(clean, market)
                handover = eval_out.get("handover")
                if debate.get("verdict") is None and eval_out.get("arbiter"):
                    debate["verdict"] = (eval_out.get("arbiter") or {}).get("verdict")
                    debate["confidence"] = (eval_out.get("arbiter") or {}).get("confidence")
            except Exception as exc:
                logger.warning("live_document handover: %s", exc)

        return {
            "ok": True,
            "symbol": clean,
            "market": mkt,
            "updated_at": datetime.now().isoformat(),
            "traffic_lights": lights,
            "resonance": resonance,
            "debate": debate,
            "recent_events": events,
            "provenance_id": provenance_id,
            "handover": handover,
            "live": True,
        }

    def _build_traffic_lights(
        self,
        symbol: str,
        market: str,
        stock_service: Any | None,
    ) -> dict[str, Any]:
        vstatus = get_verification_status(symbol, market)
        pending_reason = get_pending_reason(symbol, market)
        data_light = "green" if vstatus == "verified" else ("red" if pending_reason else "yellow")

        tech_light = "yellow"
        agent_light = "yellow"

        return {
            "data_truth": {
                "color": data_light,
                "label": "数据真值",
                "status": vstatus,
                "detail": pending_reason or "多源校验通过",
            },
            "technical": {
                "color": tech_light,
                "label": "技术共振",
                "status": "pending",
                "detail": "由共振计实时刷新",
            },
            "agent_debate": {
                "color": agent_light,
                "label": "Agent 辩论",
                "status": "pending",
                "detail": "由仲裁共识实时刷新",
            },
        }

    def _resonance_summary(
        self,
        symbol: str,
        market: MarketCode,
        stock_service: Any | None,
    ) -> dict[str, Any]:
        if stock_service is None:
            return {"ok": False}
        try:
            from datetime import date, timedelta

            import importlib

            from app.infrastructure.providers.rust_indicators import RustIndicatorProvider

            reducer_mod = importlib.import_module(
                "app.modules.strategy.services.analytics.visual_data_reducer_service"
            )
            end_d = date.today()
            start_d = end_d - timedelta(days=120)
            history = stock_service.get_history(
                symbol, market, start_d.isoformat(), end_d.isoformat()
            )
            items = history if isinstance(history, list) else (history or {}).get("history", [])
            payload = reducer_mod.TechnicalResonanceMeter(
                RustIndicatorProvider()
            ).calculate_resonance(items)
            payload["ok"] = True
            return payload
        except Exception as exc:
            logger.warning("live_document resonance: %s", exc)
            return {"ok": False, "error": str(exc)}

    def _debate_section(self, symbol: str, market: str) -> dict[str, Any]:
        rounds = get_recent_debate_rounds(symbol, market, limit=8, min_confidence=0.0)
        verdict = ""
        confidence = 0.0
        if rounds:
            bullish = sum(1 for r in rounds if r.get("stance") == "bullish")
            bearish = sum(1 for r in rounds if r.get("stance") == "bearish")
            if bullish > bearish:
                verdict = "bullish"
            elif bearish > bullish:
                verdict = "bearish"
            else:
                verdict = "neutral"
            confidence = round(
                sum(float(r.get("confidence") or 0.5) for r in rounds) / len(rounds),
                2,
            )
        return {
            "rounds": rounds[-6:],
            "round_count": len(rounds),
            "verdict": verdict or None,
            "confidence": confidence,
        }

    def _recent_symbol_events(self, symbol: str, market: str) -> list[dict[str, Any]]:
        sym_u = symbol.upper()
        code6 = SymbolNormalizer.normalize_code(symbol)
        hits: list[dict[str, Any]] = []
        for item in get_event_bus().list_recent_events(limit=80):
            data = item.get("data") or {}
            esym = str(data.get("symbol") or "").upper()
            if not esym:
                continue
            if esym not in (sym_u, code6, symbol.lower()) and code6 not in esym:
                continue
            hits.append(
                {
                    "event": item.get("event"),
                    "timestamp": item.get("timestamp"),
                    "summary": self._event_summary(item),
                }
            )
        return hits[:12]

    @staticmethod
    def _event_summary(item: dict[str, Any]) -> str:
        name = item.get("event") or ""
        data = item.get("data") or {}
        if name == "DebateRoundEvent":
            return f"{data.get('agent_role')} · {data.get('stance')}"
        if name == "ArbiterConsensusEvent":
            return f"共识 {data.get('verdict')} conf={data.get('confidence')}"
        if name == "TruthDeviationEvent":
            return f"真值偏差 {data.get('diff_pct')}%"
        if name == "CorrectionIntentEvent":
            return f"修正意图 {data.get('change_type')}"
        return name

    def apply_lights_from_payload(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Fill technical/agent light colors from resonance & debate."""
        lights = doc.get("traffic_lights") or {}
        res = doc.get("resonance") or {}
        debate = doc.get("debate") or {}

        sig = str(res.get("signal") or "neutral")
        if "buy" in sig:
            tech_color = "green"
        elif "sell" in sig:
            tech_color = "red"
        else:
            tech_color = "yellow"
        if lights.get("technical"):
            lights["technical"]["color"] = tech_color
            lights["technical"]["status"] = res.get("signal_label") or sig
            lights["technical"]["detail"] = f"共振 {res.get('resonance_score', 0)}%"

        verdict = str(debate.get("verdict") or "")
        if verdict == "bullish":
            agent_color = "green"
        elif verdict == "bearish":
            agent_color = "red"
        else:
            agent_color = "yellow"
        if lights.get("agent_debate"):
            lights["agent_debate"]["color"] = agent_color
            lights["agent_debate"]["status"] = verdict or "neutral"
            lights["agent_debate"]["detail"] = (
                f"置信度 {debate.get('confidence', 0)}" if verdict else "等待辩论轮次"
            )
        doc["traffic_lights"] = lights
        return doc
