from __future__ import annotations

"""AI analysis application service."""

from collections.abc import Iterator
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from app.core.base_service import BaseApplicationService
from app.core.utils.performance import track_latency
from app.domain.dto.decision_context_dto import DecisionContextDTO, EvidenceNoteDTO
from app.domain.enums import MarketCode
from app.domain.ports.ai_analysis_port import AiAnalysisPort
from app.modules.ai_agent.services.sentiment_fingpt_payload import build_sentiment_payload_from_analyst_report

if TYPE_CHECKING:
    from app.modules.ai_agent.services.fingpt_application_service import FinGPTApplicationService
    from app.modules.market_data.services.stock_service import StockApplicationService


import logging

logger = logging.getLogger(__name__)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class AiAnalysisService(BaseApplicationService):
    """Builds AI analysis from market, indicators and news context."""

    def __init__(
        self,
        stock_service: StockApplicationService,
        ai_adapter: AiAnalysisPort,
        *,
        fingpt_application_service: FinGPTApplicationService | None = None,
        system_health_banner_service: Any | None = None,
        parameter_store: Any | None = None,
        strategy_sop_service: Any | None = None,
        prompt_evolution_service: Any | None = None,
    ) -> None:
        super().__init__()
        self._stock_service = stock_service
        self._ai_adapter = ai_adapter
        self._fingpt = fingpt_application_service
        self._health_banner = system_health_banner_service
        self._param_store = parameter_store
        self._sop_service = strategy_sop_service
        self._prompt_evolution = prompt_evolution_service

    def _prompt_metadata(self) -> dict[str, Any]:
        if self._prompt_evolution is None or not hasattr(self._prompt_evolution, "get_current_prompt_snapshot"):
            return {}
        try:
            return self._prompt_evolution.get_current_prompt_snapshot()
        except Exception as exc:
            logger.debug("ai_analysis_service.prompt_metadata: %s", exc)
            return {}

    @track_latency("ai_analysis_analyze")
    def analyze(
        self,
        symbol: str,
        market: MarketCode,
        *,
        user_hypothesis: str | None = None,
        hypothesis_id: str | None = None,
    ) -> dict[str, Any]:
        detail = self._stock_service.get_stock_detail(symbol, market)

        # Handle StockDetailResult - convert to dict if needed
        if hasattr(detail, "model_dump"):
            detail_dict = detail.model_dump()
        elif hasattr(detail, "to_dict"):
            detail_dict = detail.to_dict()
        else:
            detail_dict = {"profile": {}, "indicators": {}}

        profile = detail_dict.get("profile", {}) or {}

        # Try to get news from stock service
        news = []
        industry_news = []
        try:
            if hasattr(self._stock_service, "get_news_snapshot"):
                snapshot = self._stock_service.get_news_snapshot(symbol, market)
                if snapshot:
                    if hasattr(snapshot, "model_dump"):
                        snap_data = snapshot.model_dump()
                    else:
                        snap_data = dict(snapshot) if hasattr(snapshot, "__dict__") else {}
                    news = snap_data.get("news", []) or []
        except Exception as e:
            logger.warning("ai_analysis_service.py.analyze: %s", e)

        context = {
            "quote": profile.get("realtime", {}),
            "indicators": detail_dict.get("indicators", {}) or {},
            "news": news,
            "industry_news": industry_news,
        }
        prompt_meta = self._prompt_metadata()
        ai_payload = self._ai_adapter.analyze(symbol=symbol, market=market.value, context=context, **prompt_meta)

        if isinstance(ai_payload, dict) and ai_payload.get("degraded"):
            try:
                from app.core.middleware.degraded_context import mark_system_degraded

                mark_system_degraded(str(ai_payload.get("mode") or "ollama"))
            except Exception as exc:
                logger.debug("ai_analysis_service.analyze degraded mark: %s", exc)
        result = {
            "symbol": symbol,
            "market": market.value,
            "generated_at": context["quote"].get("updated_at", ""),
            "context": context,
            "ai": ai_payload,
        }
        hypothesis_eval = self._maybe_evaluate_hypothesis(
            detail_dict,
            market=market,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )
        if hypothesis_eval is not None:
            result["hypothesis_evaluation"] = hypothesis_eval
        coverage = self._assess_data_coverage(symbol, market)
        result["data_coverage"] = coverage
        if (
            hypothesis_eval
            and coverage.get("level") in ("partial", "poor")
            and coverage.get("confidence_penalty")
        ):
            penalty = float(coverage["confidence_penalty"])
            hypothesis_eval["confidence"] = round(
                max(0.0, float(hypothesis_eval.get("confidence") or 0) - penalty),
                2,
            )
        self._maybe_record_fingpt_sentiment(symbol, market, ai_payload)

        # Phase 3.2: Close the Fast Path Loop
        # Push AI-derived parameters to the Reflex Map
        self._sync_reflex_parameters(symbol, market, ai_payload)

        decision = self._build_decision_context(
            symbol=symbol,
            market=market,
            context=context,
            ai_payload=ai_payload,
            hypothesis_eval=hypothesis_eval,
            coverage=coverage,
        )
        result["decision_id"] = decision.decision_id
        result["decision"] = decision.model_dump()
        try:
            from app.modules.system.services.ui.decision_trace_service import get_decision_trace_service

            get_decision_trace_service().record(decision)
        except Exception as exc:
            logger.warning("ai_analysis_service.analyze trace record: %s", exc)
        return result

    def analyze_stream(
        self,
        symbol: str,
        market: MarketCode,
        *,
        user_hypothesis: str | None = None,
        hypothesis_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield reasoning trace steps for SSE clients (Phase 4 prototype)."""
        yield {"event": "step", "phase": "market_data", "status": "started", "symbol": symbol, "ts": _utcnow_iso()}

        detail = self._stock_service.get_stock_detail(symbol, market)
        if hasattr(detail, "model_dump"):
            detail_dict = detail.model_dump()
        elif hasattr(detail, "to_dict"):
            detail_dict = detail.to_dict()
        else:
            detail_dict = {"profile": {}, "indicators": {}}

        profile = detail_dict.get("profile", {}) or {}
        news: list[Any] = []
        try:
            if hasattr(self._stock_service, "get_news_snapshot"):
                snapshot = self._stock_service.get_news_snapshot(symbol, market)
                if snapshot:
                    snap_data = (
                        snapshot.model_dump()
                        if hasattr(snapshot, "model_dump")
                        else dict(snapshot) if hasattr(snapshot, "__dict__") else {}
                    )
                    news = snap_data.get("news", []) or []
        except Exception as exc:
            logger.warning("ai_analysis_service.analyze_stream news: %s", exc)

        quote = profile.get("realtime", {}) or {}
        yield {
            "event": "evidence",
            "source": "quote",
            "title": str(quote.get("name") or symbol),
            "payload": quote,
            "ts": _utcnow_iso(),
        }

        for idx, item in enumerate(news[:5]):
            if isinstance(item, dict):
                note = EvidenceNoteDTO(
                    source="news",
                    title=str(item.get("title") or item.get("summary") or ""),
                    payload=item,
                )
                yield {"event": "evidence", "index": idx, **note.model_dump(), "ts": _utcnow_iso()}

        context = {
            "quote": quote,
            "indicators": detail_dict.get("indicators", {}) or {},
            "news": news,
            "industry_news": [],
        }
        yield {"event": "step", "phase": "llm", "status": "started", "ts": _utcnow_iso()}
        prompt_meta = self._prompt_metadata()
        if prompt_meta:
            yield {"event": "prompt", **prompt_meta, "ts": _utcnow_iso()}

        ai_payload = self._ai_adapter.analyze(symbol=symbol, market=market.value, context=context, **prompt_meta)


        if isinstance(ai_payload, dict) and ai_payload.get("degraded"):
            try:
                from app.core.middleware.degraded_context import mark_system_degraded

                mark_system_degraded(str(ai_payload.get("mode") or "ollama"))
            except Exception as exc:
                logger.debug("ai_analysis_service.analyze_stream degraded: %s", exc)
            from app.core.middleware.health_aware import build_degraded_user_message

            yield {"event": "notice", "message": build_degraded_user_message(), "ts": _utcnow_iso()}

        if self._health_banner is not None:
            try:
                banner = self._health_banner.build_banner()
                if banner.get("level") in ("critical", "warning"):
                    yield {"event": "notice", "type": "health_banner", **banner, "ts": _utcnow_iso()}
            except Exception as exc:
                logger.debug("ai_analysis_service.analyze_stream health_banner: %s", exc)

        coverage = self._assess_data_coverage(symbol, market)
        cov_note = EvidenceNoteDTO(
            source="data_coverage",
            title=str(coverage.get("level") or "unknown"),
            confidence=coverage.get("confidence_penalty"),
            payload=coverage,
        )
        yield {"event": "evidence", **cov_note.model_dump(), "ts": _utcnow_iso()}

        hypothesis_eval = self._maybe_evaluate_hypothesis(
            detail_dict,
            market=market,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )
        decision = self._build_decision_context(
            symbol=symbol,
            market=market,
            context=context,
            ai_payload=ai_payload,
            hypothesis_eval=hypothesis_eval,
            coverage=coverage,
        )
        try:
            from app.modules.system.services.ui.decision_trace_service import get_decision_trace_service

            get_decision_trace_service().record(decision)
        except Exception as exc:
            logger.warning("ai_analysis_service.analyze_stream trace: %s", exc)

        result = {
            "symbol": symbol,
            "market": market.value,
            "ai": ai_payload,
            "decision_id": decision.decision_id,
            "decision": decision.model_dump(),
        }
        yield {"event": "complete", "data": result, "ts": _utcnow_iso()}

    @staticmethod
    def _build_decision_context(
        *,
        symbol: str,
        market: MarketCode,
        context: dict[str, Any],
        ai_payload: dict[str, Any],
        hypothesis_eval: dict[str, Any] | None,
        coverage: dict[str, Any],
    ) -> DecisionContextDTO:
        """Build structured provenance for replay and attribution."""
        analysis_text = str((ai_payload or {}).get("analysis") or "").strip()
        reasoning_trace: list[str] = []
        if analysis_text:
            reasoning_trace.append(analysis_text[:2000])
        if hypothesis_eval:
            verdict = hypothesis_eval.get("verdict") or hypothesis_eval.get("summary")
            if verdict:
                reasoning_trace.append(f"hypothesis: {verdict}")

        evidence: list[EvidenceNoteDTO] = []
        for item in (context.get("news") or [])[:5]:
            if isinstance(item, dict):
                evidence.append(
                    EvidenceNoteDTO(
                        source="news",
                        title=str(item.get("title") or item.get("summary") or ""),
                        payload=item,
                    )
                )
        for item in (context.get("industry_news") or [])[:3]:
            if isinstance(item, dict):
                evidence.append(
                    EvidenceNoteDTO(
                        source="industry_news",
                        title=str(item.get("title") or item.get("summary") or ""),
                        payload=item,
                    )
                )
        if coverage:
            evidence.append(
                EvidenceNoteDTO(
                    source="data_coverage",
                    title=str(coverage.get("level") or "unknown"),
                    confidence=coverage.get("confidence_penalty"),
                    payload=coverage,
                )
            )

        model_version = str(
            (ai_payload or {}).get("mode")
            or (ai_payload or {}).get("model")
            or "unknown"
        )
        return DecisionContextDTO(
            decision_id=f"decision_{uuid4().hex[:12]}",
            subject=f"{market.value}:{symbol}",
            model_version=model_version,
            input_snapshot={
                "symbol": symbol,
                "market": market.value,
                "quote": context.get("quote") or {},
                "indicators": context.get("indicators") or {},
                "hypothesis_evaluation": hypothesis_eval,
                "data_coverage": coverage,
            },
            reasoning_trace=reasoning_trace,
            evidence=evidence,
        )

    def _assess_data_coverage(self, symbol: str, market: MarketCode) -> dict[str, Any]:
        from app.modules.market_data.services.data_coverage_service import DataCoverageService

        dto = DataCoverageService(self._stock_service).assess_symbol(symbol, market)
        return dto.model_dump()

    @staticmethod
    def _maybe_evaluate_hypothesis(
        detail: dict[str, Any],
        *,
        market: MarketCode,
        user_hypothesis: str | None,
        hypothesis_id: str | None,
    ) -> dict[str, Any] | None:
        from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import (
            HypothesisEvaluationService,
        )

        svc = HypothesisEvaluationService()
        dto = svc.evaluate(
            symbol=str(detail.get("symbol") or ""),
            detail=detail,
            hypothesis_id=hypothesis_id,
            user_hypothesis=user_hypothesis,
            market=market.value,
        )
        return dto.model_dump() if dto is not None else None

    def _maybe_record_fingpt_sentiment(
        self,
        symbol: str,
        market: MarketCode,
        ai_payload: dict[str, Any],
    ) -> None:
        if self._fingpt is None or not self._fingpt.can_write_ai_analyze():
            return
        narrative = str((ai_payload or {}).get("analysis") or "").strip()
        if not narrative:
            return
        ticker = f"{market.value}:{symbol}".strip()
        try:
            payload = build_sentiment_payload_from_analyst_report(narrative)
            payload["summary"] = f"[ai_analyze:{ai_payload.get('mode','')}] " + str(payload.get("summary", ""))
            payload["summary"] = payload["summary"][:4000]
            payload["source"] = "ai_analyze"
            payload["source_ref"] = str(ai_payload.get("mode") or "").strip() or None
            rec = self._fingpt.record_sentiment(ticker, payload)
            if not rec.get("ok"):
                self.logger.warning("FinGPT record_sentiment (ai_analyze) not ok: %s", rec.get("error"))
        except Exception as exc:
            self.logger.exception("FinGPT ai_analyze sentiment persist failed: %s", exc)

    def _sync_reflex_parameters(self, symbol: str, market: MarketCode, ai_payload: dict[str, Any]) -> None:
        """Push AI findings to the FastPathParameterStore for microsecond access."""
        if self._param_store is None:
            return

        try:
            # Extract numbers from AI narrative or structured payload
            verdict = (ai_payload or {}).get("verdict", {})

            # 1. Update stop distance (Reflex Path: Pre-Trade Validation)
            stop_dist = verdict.get("suggested_stop_distance", 0.02)
            self._param_store.set_parameter(symbol, "stop_distance", stop_dist)

            # 2. Update risk multiplier (Reflex Path: Position Sizing)
            risk_mult = verdict.get("risk_multiplier", 1.0)
            self._param_store.set_parameter(symbol, "risk_multiplier", risk_mult)

            # 3. Apply SOP (Strategy Operating Procedure) if available
            if self._sop_service:
                try:
                    sop_params = self._sop_service.compute_reflex_params(symbol, ai_payload, archetype="conservative")
                    # SOP may provide trigger specifics
                    if sop_params.trigger_price is not None:
                        self._param_store.set_parameter(symbol, "trigger_price", sop_params.trigger_price)
                    if sop_params.trigger_side is not None:
                        self._param_store.set_parameter(symbol, "trigger_side", sop_params.trigger_side)
                    if sop_params.trigger_qty:
                        self._param_store.set_parameter(symbol, "trigger_qty", sop_params.trigger_qty)
                    # SOP can also adjust stop distance or risk multiplier
                    if sop_params.stop_distance is not None:
                        self._param_store.set_parameter(symbol, "stop_distance", sop_params.stop_distance)
                    if sop_params.risk_multiplier is not None:
                        self._param_store.set_parameter(symbol, "risk_multiplier", sop_params.risk_multiplier)
                except Exception as sop_err:
                    logger.warning("SOP computation failed for %s: %s", symbol, sop_err)

            logger.debug("FastPath Sync [%s]: stop=%s, risk=%s", symbol, stop_dist, risk_mult)
        except Exception as e:
            logger.warning("FastPath Sync failed for %s: %s", symbol, e)
