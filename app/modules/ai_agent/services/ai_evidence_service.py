from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""AI evidence and trust service.

Builds an auditable evidence bundle for AI conclusions without triggering new
LLM inference. The bundle combines market data, news, FinGPT records,
observation-loop outcomes and user feedback.
"""


import json
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.domain.verification import get_pending_reason, get_verification_status

logger = get_logger(__name__)


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _to_dict(value: object) -> GenericResponseDTO:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


class AiEvidenceService:
    """Build and record AI trust evidence bundles."""

    def __init__(
        self,
        *,
        market_service: object,
        stock_service: object,
        fingpt_application_service: Any | None = None,
        signal_observation_service: Any | None = None,
        feedback_store_path: Path,
    ) -> None:
        self._market_service = market_service
        self._stock_service = stock_service
        self._fingpt = fingpt_application_service
        self._observations = signal_observation_service
        self._feedback_store_path = Path(feedback_store_path)
        self._feedback_store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def build_bundle(
        self,
        *,
        symbol: str,
        market: MarketCode = MarketCode.CN,
        include_news: bool = True,
        user_hypothesis: str | None = None,
        hypothesis_id: str | None = None,
    ) -> GenericResponseDTO:
        """Return an auditable evidence bundle for one symbol."""
        clean_symbol = str(symbol or "").strip().upper()
        if not clean_symbol:
            raise ValueError("symbol_required")
        quote = self._quote(clean_symbol, market)
        news = self._news(clean_symbol, market) if include_news else []
        fingpt = self._fingpt_records(clean_symbol, market)
        observations = self._observation_records(clean_symbol, market)
        calibration = self._calibration(fingpt.get("predictions") or [], observations)
        feedback = self.feedback_summary(symbol=clean_symbol, market=market)
        from app.modules.market_data.services.data_coverage_service import DataCoverageService

        coverage_dto = DataCoverageService(self._stock_service).assess_symbol(clean_symbol, market)
        bull_bear = self._bull_bear_summary(quote, news, fingpt, observations)
        trust = self._trust_score(
            quote=quote,
            news=news,
            fingpt=fingpt,
            observations=observations,
            feedback=feedback,
            coverage=coverage_dto,
        )
        verification_status = get_verification_status(clean_symbol, market.value)
        bundle: GenericResponseDTO = {
            "generated_at": _now_str(),
            "symbol": clean_symbol,
            "market": market.value,
            "verification_status": verification_status,
            "verification_note": get_pending_reason(clean_symbol, market.value),
            "quote": quote,
            "news": news,
            "fingpt": fingpt,
            "observations": observations,
            "calibration": calibration,
            "feedback": feedback,
            "bull_bear": bull_bear,
            "trust": trust,
            "data_coverage": coverage_dto.model_dump(),
        }
        hypo = self._hypothesis_evaluation(
            symbol=clean_symbol,
            market=market,
            quote=quote,
            user_hypothesis=user_hypothesis,
            hypothesis_id=hypothesis_id,
        )
        if hypo is not None:
            bundle["hypothesis_evaluation"] = hypo
        return bundle

    def _hypothesis_evaluation(
        self,
        *,
        symbol: str,
        market: MarketCode,
        quote: dict[str, Any],
        user_hypothesis: str | None,
        hypothesis_id: str | None,
    ) -> dict[str, Any] | None:
        from app.modules.ai_agent.services.analysis.hypothesis_evaluation_service import (
            HypothesisEvaluationService,
        )

        svc = HypothesisEvaluationService()
        detail: dict[str, Any] = {"profile": {"realtime": quote}, "indicators": {}}
        try:
            raw = self._stock_service.get_stock_detail(symbol, market)
            if hasattr(raw, "model_dump"):
                detail = raw.model_dump()
            elif isinstance(raw, dict):
                detail = raw
        except Exception as exc:  # noqa: BLE001
            logger.warning("hypothesis eval detail unavailable for %s: %s", symbol, exc)
        dto = svc.evaluate(
            symbol=symbol,
            detail=detail,
            hypothesis_id=hypothesis_id,
            user_hypothesis=user_hypothesis,
            market=market.value,
        )
        return dto.model_dump() if dto is not None else None

    def record_feedback(
        self,
        *,
        symbol: str,
        market: MarketCode,
        vote: str,
        comment: str = "",
        source: str = "ai_evidence",
        user_id: str | None = None,
    ) -> GenericResponseDTO:
        """Record user feedback for AI evidence usefulness."""
        clean_vote = str(vote or "").strip().lower()
        if clean_vote not in ("useful", "not_useful", "neutral"):
            raise ValueError("vote_must_be_useful_not_useful_or_neutral")
        row = {
            "id": uuid.uuid4().hex[:12],
            "symbol": str(symbol or "").strip().upper(),
            "market": market.value,
            "vote": clean_vote,
            "comment": str(comment or "").strip()[:1000],
            "source": str(source or "ai_evidence").strip()[:80],
            "user_id": str(user_id or "").strip() or None,
            "created_at": _now_str(),
        }
        with self._lock:
            rows = self._read_feedback()
            rows.append(row)
            self._write_feedback(rows)
        return row

    def feedback_summary(self, *, symbol: str, market: MarketCode) -> GenericResponseDTO:
        """Return aggregate user feedback for one symbol."""
        clean_symbol = str(symbol or "").strip().upper()
        rows = [
            r for r in self._read_feedback()
            if r.get("symbol") == clean_symbol and r.get("market") == market.value
        ]
        useful = len([r for r in rows if r.get("vote") == "useful"])
        not_useful = len([r for r in rows if r.get("vote") == "not_useful"])
        neutral = len([r for r in rows if r.get("vote") == "neutral"])
        total = len(rows)
        return {
            "total": total,
            "useful": useful,
            "not_useful": not_useful,
            "neutral": neutral,
            "useful_rate": round(useful / total * 100, 2) if total else 0,
            "recent": rows[-5:],
        }

    def _quote(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        try:
            quotes = self._market_service.list_quotes(market, [symbol])
            if quotes:
                return _to_dict(quotes[0])
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI evidence quote unavailable for %s: %s", symbol, exc)
        return {"code": symbol, "name": symbol}

    def _news(self, symbol: str, market: MarketCode) -> list[dict[str, Any]]:
        try:
            snapshot = self._stock_service.get_news_snapshot(symbol, market)
            data = snapshot.model_dump() if hasattr(snapshot, "model_dump") else _to_dict(snapshot)
            rows = []
            for item in (data.get("news") or [])[:8]:
                rows.append(
                    {
                        "title": item.get("title") or "",
                        "source": item.get("source") or "",
                        "time": item.get("time") or item.get("published_at") or "",
                        "url": item.get("url") or "",
                    }
                )
            return rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI evidence news unavailable for %s: %s", symbol, exc)
            return []

    def _fingpt_records(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        if self._fingpt is None or not self._fingpt.is_available():
            return {"available": False, "predictions": [], "sentiments": []}
        tickers = [symbol, f"{market.value}:{symbol}"]
        predictions: list[dict[str, Any]] = []
        sentiments: list[dict[str, Any]] = []
        for ticker in tickers:
            pred = self._fingpt.list_recent_predictions(limit=8, ticker=ticker, since_hours=24 * 90)
            sent = self._fingpt.list_recent_sentiments(limit=8, ticker=ticker, since_hours=24 * 90)
            predictions.extend(pred.get("items") or [])
            sentiments.extend(sent.get("items") or [])
        return {
            "available": True,
            "predictions": self._dedupe_by_id(predictions)[:8],
            "sentiments": self._dedupe_by_id(sentiments)[:8],
        }

    def _observation_records(self, symbol: str, market: MarketCode) -> GenericResponseDTO:
        if self._observations is None:
            return {"available": False, "items": []}
        try:
            rows = self._observations.list_observations(status="all", refresh=True).get("items") or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI evidence observations unavailable: %s", exc)
            rows = []
        clean_symbol = str(symbol or "").strip().upper()
        items = [
            r for r in rows
            if str(r.get("symbol") or "").strip().upper() == clean_symbol
            and str(r.get("market") or market.value) == market.value
        ]
        return {"available": True, "items": items[:10]}

    def _calibration(
        self,
        predictions: list[dict[str, Any]],
        observations: dict[str, Any],
    ) -> GenericResponseDTO:
        obs_items = observations.get("items") or []
        closed = [r for r in obs_items if r.get("status") == "closed" or r.get("trigger_status") in ("target_hit", "stop_hit")]
        target_hits = len([r for r in obs_items if r.get("trigger_status") == "target_hit"])
        stop_hits = len([r for r in obs_items if r.get("trigger_status") == "stop_hit"])
        avg_return = 0.0
        if obs_items:
            avg_return = sum(_safe_float(r.get("return_pct")) for r in obs_items) / len(obs_items)
        return {
            "prediction_samples": len(predictions),
            "observation_samples": len(obs_items),
            "closed_or_triggered": len(closed),
            "target_hits": target_hits,
            "stop_hits": stop_hits,
            "target_hit_rate": round(target_hits / max(len(obs_items), 1) * 100, 2) if obs_items else 0,
            "stop_hit_rate": round(stop_hits / max(len(obs_items), 1) * 100, 2) if obs_items else 0,
            "avg_observation_return_pct": round(avg_return, 2),
            "note": "基于平台内FinGPT 记录与模拟观察单估算，不代表真实交易胜率。",
        }

    def _trust_score(
        self,
        *,
        quote: dict[str, Any],
        news: list[dict[str, Any]],
        fingpt: dict[str, Any],
        observations: dict[str, Any],
        feedback: dict[str, Any],
        coverage: Any | None = None,
    ) -> GenericResponseDTO:
        score = 40
        reasons: list[str] = []
        if quote.get("price"):
            score += 12
            reasons.append("有实时行情快照")
        if news:
            score += min(len(news) * 3, 15)
            reasons.append(f"�?{len(news)} 条新闻证�")
        if fingpt.get("predictions"):
            score += 12
            reasons.append("有历�?FinGPT 预测记录")
        if fingpt.get("sentiments"):
            score += 8
            reasons.append("有历史情感摘要记�")
        if observations.get("items"):
            score += 10
            reasons.append("有模拟观察单反馈")
        if feedback.get("total"):
            score += 5 if feedback.get("useful_rate", 0) >= 50 else -5
            reasons.append("已有用户反馈")
        if coverage is not None:
            level = getattr(coverage, "level", None) or (coverage.get("level") if isinstance(coverage, dict) else "")
            penalty = float(getattr(coverage, "confidence_penalty", 0) or 0)
            if isinstance(coverage, dict):
                penalty = float(coverage.get("confidence_penalty") or 0)
            if level == "poor":
                score -= int(penalty * 100)
                reasons.append("K 线覆盖不足，置信度降�")
            elif level == "partial":
                score -= int(penalty * 60)
                reasons.append("K 线覆盖一�")
            elif level == "good":
                reasons.append("近端 K 线覆盖良�")
        score = max(0, min(score, 100))
        level = "高" if score >= 75 else "中" if score >= 55 else "低"
        return {"score": score, "level": level, "reasons": reasons}

    def _bull_bear_summary(
        self,
        quote: dict[str, Any],
        news: list[dict[str, Any]],
        fingpt: dict[str, Any],
        observations: dict[str, Any],
    ) -> GenericResponseDTO[str, list[str]]:
        change_pct = _safe_float(quote.get("change_pct"))
        bull: list[str] = []
        bear: list[str] = []
        if change_pct >= 2:
            bull.append("当日涨幅偏强，市场短线认可度较高")
        elif change_pct <= -2:
            bear.append("当日跌幅偏弱，需要确认是否存在基本面或情绪压�")
        if news:
            bull.append("存在可追溯新闻材料，可进一步核验事件驱�")
        if fingpt.get("predictions"):
            bull.append("有历史预测记录可与当前结论对�")
        else:
            bear.append("缺少历史预测样本，AI 结论校准不足")
        obs_items = observations.get("items") or []
        if any(_safe_float(x.get("return_pct")) > 0 for x in obs_items):
            bull.append("模拟观察单已有正收益样本")
        if any(x.get("trigger_status") == "stop_hit" for x in obs_items):
            bear.append("模拟观察单曾触发止损，需要复核策略适配�")
        return {
            "bull": bull[:5] or ["暂无明确看多证据"],
            "bear": bear[:5] or ["暂无明确看空证据"],
        }

    def _dedupe_by_id(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        out = []
        for row in rows:
            key = row.get("id") or json.dumps(row, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out

    def _read_feedback(self) -> list[dict[str, Any]]:
        if not self._feedback_store_path.exists():
            return []
        try:
            raw = json.loads(self._feedback_store_path.read_text(encoding="utf-8"))
            if isinstance(raw, list):
                return [dict(x) for x in raw if isinstance(x, dict)]
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI evidence feedback read failed: %s", exc)
        return []

    def _write_feedback(self, rows: list[dict[str, Any]]) -> None:
        self._feedback_store_path.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
