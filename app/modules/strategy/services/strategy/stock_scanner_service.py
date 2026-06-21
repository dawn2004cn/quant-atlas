from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Stock scanner service using domain models and events."""


from typing import Any
from datetime import datetime

from app.core.logger import get_logger
from app.domain.models.signal_models import SignalGenerator, SignalType
from app.domain.models.risk_models import RiskCalculator
from app.application.dto.complete_dto import ScanResultDTO, SignalDTO
from app.application.events import EventType, publish_event

logger = get_logger(__name__)


class StockScannerService:
    """Scanner service that uses domain models for signal generation."""

    def __init__(self, market_provider=None):
        self._market_provider = market_provider
        self._scan_results: dict[str, list[SignalDTO]] = {}
        logger.info("StockScannerService initialized")

    async def scan_breakout_stocks(
        self,
        stocks: list[dict[str, Any]],
        min_volume_ratio: float = 1.5,
        min_price_change: float = 3.0,
    ) -> ScanResultDTO:
        """Scan for breakout signals."""
        signals = []

        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            price = stock.get("price", 0)
            volume = stock.get("volume", 0)
            high = stock.get("high", price)
            low = stock.get("low", price)
            open_price = stock.get("open", price)
            prev_close = stock.get("prev_close", price)
            avg_volume = stock.get("avg_volume_20d", volume or 1)

            volume_ratio = volume / avg_volume if avg_volume > 0 else 0
            price_change = ((price - prev_close) / prev_close * 100) if prev_close > 0 else 0

            if volume_ratio >= min_volume_ratio and abs(price_change) >= min_price_change:
                signal = SignalGenerator.generate_breakout_signal(
                    code=code,
                    name=name,
                    price=price,
                    volume=volume,
                    high=high,
                    low=low,
                    open_price=open_price,
                    prev_close=prev_close,
                    avg_volume_20d=avg_volume,
                )

                signals.append(SignalDTO(
                    id=signal.id,
                    code=signal.code,
                    name=signal.name,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    direction=signal.direction.value,
                    price=signal.price,
                    confidence=signal.confidence,
                    reason=signal.reason,
                    generated_at=signal.generated_at.isoformat(),
                ))

        result = ScanResultDTO(
            scan_name="breakout",
            signals=signals,
            total_scanned=len(stocks),
            matched=len(signals),
        )

        await publish_event(
            EventType.SCAN_COMPLETED,
            {"scan_name": "breakout", "total": len(stocks), "matched": len(signals)},
            source="StockScannerService"
        )

        return result

    async def scan_volume_stocks(
        self,
        stocks: list[dict[str, Any]],
        min_volume_ratio: float = 2.0,
    ) -> ScanResultDTO:
        """Scan for volume-based signals."""
        signals = []

        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            price = stock.get("price", 0)
            volume = stock.get("volume", 0)
            avg_volume = stock.get("avg_volume_20d", volume or 1)

            volume_ratio = volume / avg_volume if avg_volume > 0 else 0

            if volume_ratio >= min_volume_ratio:
                signal = SignalGenerator.generate_volume_signal(
                    code=code,
                    name=name,
                    price=price,
                    volume=volume,
                    avg_volume_20d=avg_volume,
                )

                signals.append(SignalDTO(
                    id=signal.id,
                    code=signal.code,
                    name=signal.name,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    direction=signal.direction.value,
                    price=signal.price,
                    confidence=signal.confidence,
                    generated_at=signal.generated_at.isoformat(),
                ))

        return ScanResultDTO(
            scan_name="volume",
            signals=signals,
            total_scanned=len(stocks),
            matched=len(signals),
        )

    async def scan_momentum_stocks(
        self,
        stocks: list[dict[str, Any]],
        min_change_pct: float = 5.0,
    ) -> ScanResultDTO:
        """Scan for momentum signals."""
        signals = []

        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            price = stock.get("price", 0)
            change_pct = stock.get("change_pct", 0)
            rsi = stock.get("rsi")
            macd = stock.get("macd")

            if abs(change_pct) >= min_change_pct:
                signal = SignalGenerator.generate_momentum_signal(
                    code=code,
                    name=name,
                    price=price,
                    change_pct=change_pct,
                    rsi=rsi,
                    macd=macd,
                )

                signals.append(SignalDTO(
                    id=signal.id,
                    code=signal.code,
                    name=signal.name,
                    signal_type=signal.signal_type.value,
                    strength=signal.strength.value,
                    direction=signal.direction.value,
                    price=signal.price,
                    confidence=signal.confidence,
                    generated_at=signal.generated_at.isoformat(),
                ))

        return ScanResultDTO(
            scan_name="momentum",
            signals=signals,
            total_scanned=len(stocks),
            matched=len(signals),
        )

    async def scan_low_risk_stocks(
        self,
        stocks: list[dict[str, Any]],
        max_risk_score: float = 30.0,
    ) -> ScanResultDTO:
        """Scan for low-risk stocks."""
        signals = []

        for stock in stocks:
            code = stock.get("code", "")
            name = stock.get("name", "")
            price = stock.get("price", 0)
            volatility = stock.get("volatility", 0.2)
            beta = stock.get("beta", 1.0)

            risk = RiskCalculator.calculate_position_risk(
                position_value=price * 1000,
                portfolio_value=100000,
                weight=0.01,
                volatility=volatility,
            )

            if risk.risk_score <= max_risk_score:
                signals.append(SignalDTO(
                    code=code,
                    name=name,
                    signal_type="low_risk",
                    strength="moderate",
                    direction="long",
                    price=price,
                    confidence=100 - risk.risk_score,
                    reason=f"Risk score: {risk.risk_score:.1f}, Beta: {beta:.2f}",
                ))

        return ScanResultDTO(
            scan_name="low_risk",
            signals=signals,
            total_scanned=len(stocks),
            matched=len(signals),
        )

    def get_scan_history(self, scan_name: str | None = None) -> GenericResponseDTO[str, object]:
        """Get scan history."""
        if scan_name:
            return {"scan_name": scan_name, "results": self._scan_results.get(scan_name, [])}
        return self._scan_results


__all__ = ["StockScannerService"]