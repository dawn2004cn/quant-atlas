"""Mappers - Domain to DTO conversion.

Converts domain entities to DTOs for API responses.
"""


from app.domain.repositories import Stock, Signal
from app.application.interfaces import StockDTO, SignalDTO


class StockMapper:
    """Maps Stock entity to DTO."""

    @staticmethod
    def to_dto(
        stock: Stock,
        price: float | None = None,
        change: float | None = None,
        volume: int | None = None,
    ) -> StockDTO:
        return StockDTO(
            code=stock.code,
            name=stock.name,
            market=stock.market,
            price=price,
            change=change,
            volume=volume,
        )


class SignalMapper:
    """Maps Signal entity to DTO."""

    @staticmethod
    def to_dto(signal: Signal) -> SignalDTO:
        return SignalDTO(
            stock_code=signal.stock_code,
            signal_type=signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type),
            source=signal.source,
            confidence=signal.confidence,
            reason=signal.reason,
            created_at=signal.created_at.isoformat() if hasattr(signal.created_at, 'isoformat') else str(signal.created_at),
        )


class AnalysisResultMapper:
    """Maps analysis result to DTO."""

    @staticmethod
    def to_dto(
        stock_code: str,
        signals: list[Signal],
        summary: str,
        confidence: float,
    ) -> dict:
        return {
            "stock_code": stock_code,
            "signals": [SignalMapper.to_dto(s) for s in signals],
            "summary": summary,
            "confidence": confidence,
        }


__all__ = ["StockMapper", "SignalMapper", "AnalysisResultMapper"]
