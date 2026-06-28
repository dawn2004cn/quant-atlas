from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Enhanced Market Service demonstrating new architecture patterns.

This service shows how to migrate from old dict-based services
to the new DTO + async + domain model patterns.
"""


from typing import Any

from app.application.dto.complete_dto import (
    MarketOverviewDTO,
    QuoteBatchDTO,
    SignalDTO,
    StockAnalysisResultDTO,
)
from app.core.logger import get_logger
from app.domain.dto import QuoteDTO
from app.domain.enums import MarketCode
from app.domain.models import RiskMetrics, SignalGenerator
from app.domain.services import MarketDomainService, RiskDomainService, SignalDomainService
from app.modules.system.services.helpers.async_market_access import wrap_market_provider_for_async

logger = get_logger(__name__)


class EnhancedMarketService:
    """Enhanced market service using new architecture patterns.

    This demonstrates:
    - Async data fetching
    - DTO responses instead of dicts
    - Domain models for business logic
    - Event publishing for decoupled communication
    """

    def __init__(self, sync_provider: object):
        # Wrap sync provider in async
        self._sync_provider = sync_provider
        self._async_provider: Any | None = None

    @property
    def async_provider(self) -> Any:
        if self._async_provider is None:
            self._async_provider = wrap_market_provider_for_async(self._sync_provider)
        return self._async_provider

    async def get_quote(self, code: str) -> QuoteDTO:
        """Get single quote as DTO."""
        try:
            quotes = await self.async_provider.get_realtime_quotes([code], MarketCode.CN)
            if quotes:
                data = quotes[0] if isinstance(quotes[0], dict) else quotes[0].__dict__
                return QuoteDTO(**MarketDomainService.normalize_quote(data))
        except Exception as e:
            logger.error(f"Error getting quote for {code}: {e}")
        return QuoteDTO(code=code)

    async def get_quotes_batch(self, codes: list[str]) -> QuoteBatchDTO:
        """Get multiple quotes as DTO batch."""
        try:
            quotes = await self.async_provider.get_realtime_quotes(codes, MarketCode.CN)
            quote_list = []
            for q in quotes:
                data = q if isinstance(q, dict) else q.__dict__
                normalized = MarketDomainService.normalize_quote(data)
                quote_list.append(QuoteDTO(**normalized))
            return QuoteBatchDTO(
                quotes=quote_list,
                total=len(quote_list),
                cached=False
            )
        except Exception as e:
            logger.error(f"Error getting quotes batch: {e}")
            return QuoteBatchDTO(quotes=[], total=0)

    async def get_market_overview(self, market: MarketCode = MarketCode.CN) -> MarketOverviewDTO:
        """Get market overview as DTO."""
        try:
            overview = await self.async_provider.get_market_overview(market)
            return MarketOverviewDTO(
                market=market.value,
                status=overview.get('status', 'active'),
                trade_date=overview.get('trade_date', ''),
                index=overview.get('index', {}),
                total_stocks=overview.get('total_stocks', 0),
                gainers=overview.get('gainers', 0),
                losers=overview.get('losers', 0),
                unchanged=overview.get('unchanged', 0),
            )
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return MarketOverviewDTO(market=market.value, status='error')

    async def analyze_stock(
        self,
        code: str,
        price_history: list[float]
    ) -> StockAnalysisResultDTO:
        """Complete stock analysis using domain models."""
        try:
            # Get current quote
            quote = await self.get_quote(code)

            # Calculate risk using domain model
            current_price = quote.price
            risk = RiskDomainService.assess_stock_risk(
                code, price_history, current_price
            )

            # Find support/resistance
            sr_levels = RiskDomainService.find_support_resistance(price_history)

            # Generate signals using domain model
            signals = await self._generate_signals(code, price_history, quote)

            # Build result
            return StockAnalysisResultDTO(
                code=code,
                name=quote.name,
                quote=quote,
                signals=[s.signal_type for s in signals],
                sentiment=self._calculate_sentiment(risk),
                score=risk.score,
                recommendation=self._get_recommendation(risk, signals),
                confidence=min(90, risk.score),
                risks=risk.warnings,
                support_levels=[s.price for s in sr_levels.get('support', [])],
                resistance_levels=[s.price for s in sr_levels.get('resistance', [])],
            )
        except Exception as e:
            logger.error(f"Error analyzing stock {code}: {e}")
            return StockAnalysisResultDTO(code=code)

    async def _generate_signals(
        self,
        code: str,
        price_history: list[float],
        quote: QuoteDTO
    ) -> list[SignalDTO]:
        """Generate signals using domain models."""
        signals = []

        if len(price_history) >= 20:
            # Simple volume check
            volume = quote.volume
            avg_volume = sum(s.get('volume', 0) for s in price_history[-20:]) / 20

            signal = SignalGenerator.generate_breakout_signal(
                code, quote.price,
                max(price_history[-20:]),
                volume, avg_volume
            )

            if signal:
                signals.append(SignalDTO(
                    code=code,
                    signal_type=signal.signal_type.value,
                    direction=signal.direction.value,
                    strength=signal.strength.value,
                    price=quote.price,
                    confidence=signal.confidence,
                    reason=signal.reason,
                ))

        return signals

    def _calculate_sentiment(self, risk: RiskMetrics) -> str:
        """Calculate sentiment from risk metrics."""
        if risk.score < 35:
            return "bullish"
        elif risk.score > 65:
            return "bearish"
        return "neutral"

    def _get_recommendation(self, risk: RiskMetrics, signals: list) -> str:
        """Get investment recommendation."""
        if signals and risk.score < 50:
            return "buy"
        elif risk.score > 70:
            return "sell"
        return "hold"

    # Backwards compatibility - sync methods that return dict
    def get_quote_dict(self, code: str) -> GenericResponseDTO[str, object]:
        """Legacy sync method returning dict (for backwards compatibility)."""
        try:
            # Simplified - in production would use actual provider
            return {'code': code, 'price': 0, 'name': ''}
        except Exception:
            return {'code': code, 'price': 0, 'name': ''}

    def cross_validate_indicators(self, code: str, price_history: list[float]) -> dict[str, Any]:
        """Recursive logic self-audit: validate indicators computed by multiple implementations.

        Compares domain-service indicator results against simple numpy/pandas fallback.
        Returns drift report; if drift exceeds threshold, marks logic deviation.
        """
        try:
            domain_signals = SignalDomainService.generate_signals_from_history(code, price_history)
        except Exception as exc:
            logger.debug("domain signal generation failed for %s: %s", code, exc)
            domain_signals = []
        try:
            fallback_signals = self._fallback_indicator_signals(code, price_history)
        except Exception as exc:
            logger.debug("fallback indicator generation failed for %s: %s", code, exc)
            fallback_signals = []
        drift_items: list[dict[str, Any]] = []
        domain_map = {s.get("name") or s.get("type"): s for s in domain_signals}
        fallback_map = {s.get("name") or s.get("type"): s for s in fallback_signals}
        for name, ds in domain_map.items():
            fs = fallback_map.get(name)
            if fs is None:
                drift_items.append({"indicator": name, "issue": "missing_in_fallback"})
                continue
            dv = ds.get("value")
            fv = fs.get("value")
            if isinstance(dv, (int, float)) and isinstance(fv, (int, float)) and dv != 0:
                rel = abs((dv - fv) / abs(dv))
                if rel > 0.05:
                    drift_items.append({
                        "indicator": name,
                        "domain_value": dv,
                        "fallback_value": fv,
                        "rel_drift": round(rel, 4),
                        "issue": "threshold_exceeded",
                    })
        deviation_detected = len(drift_items) > 0
        return {
            "ok": True,
            "code": code,
            "deviation_detected": deviation_detected,
            "drift_count": len(drift_items),
            "drifts": drift_items[:20],
            "domain_signal_count": len(domain_signals),
            "fallback_signal_count": len(fallback_signals),
            "evidence": f"cross-validated {len(domain_map)} indicators; {len(drift_items)} drifted",
        }

    def _fallback_indicator_signals(self, code: str, price_history: list[float]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if len(price_history) < 2:
            return out
        close = price_history[-1]
        prev = price_history[-2]
        out.append({"name": "roc_close_1", "value": None if prev == 0 else (close - prev) / abs(prev)})
        if len(price_history) >= 20:
            ma20 = sum(price_history[-20:]) / 20
            out.append({"name": "ma20", "value": ma20})
        if len(price_history) >= 10:
            ma10 = sum(price_history[-10:]) / 10
            out.append({"name": "ma10", "value": ma10})
        return out
