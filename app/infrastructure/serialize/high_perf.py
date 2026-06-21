from __future__ import annotations
"""High-performance serialization using msgspec."""


import logging
from typing import Any, Dict, List, Optional


from app.core.logger import get_logger

logger = get_logger(__name__)

try:
    import msgspec
    MSGSPEC_AVAILABLE = True
except ImportError:
    MSGSPEC_AVAILABLE = False
    logger.warning("msgspec not installed. Install with: pip install msgspec")


if MSGSPEC_AVAILABLE:
    class StockQuoteProto(msgspec.Struct):
        """High-performance stock quote schema."""
        code: str
        name: str
        market: str
        price: float
        change_pct: float
        volume: float = 0.0
        amount: float = 0.0
        open_price: float = 0.0
        high_price: float = 0.0
        low_price: float = 0.0

    class StockDetailProto(msgspec.Struct):
        """High-performance stock detail schema."""
        code: str
        name: str
        price: float
        change_pct: float
        volume: float
        amount: float
        turnover: float = 0.0
        pe: float = 0.0
        pb: float = 0.0
        industry: str = ""

    class TradeSignalProto(msgspec.Struct):
        """High-performance trade signal schema."""
        symbol: str
        action: str  # "buy", "sell"
        price: float
        quantity: float
        reason: str = ""
        confidence: float = 1.0
        timestamp: str = ""

    class MarketDataUpdateProto(msgspec.Struct):
        """High-performance market data update."""
        market: str
        symbols: List[str]
        quotes: Dict[str, StockQuoteProto]
        timestamp: str


class MessageSerializer:
    """High-performance message serializer using msgspec."""

    _encoders: Dict[type, Any] = {}
    _decoders: Dict[type, Any] = {}

    @classmethod
    def get_encoder(cls, schema_type: type):
        """Get or create an encoder for a schema type."""
        if schema_type not in cls._encoders:
            if MSGSPEC_AVAILABLE:
                cls._encoders[schema_type] = msgspec.json.Encoder(schema_type)
        return cls._encoders.get(schema_type)

    @classmethod
    def get_decoder(cls, schema_type: type):
        """Get or create a decoder for a schema type."""
        if schema_type not in cls._decoders:
            if MSGSPEC_AVAILABLE:
                cls._decoders[schema_type] = msgspec.json.Decoder(schema_type)
        return cls._decoders.get(schema_type)

    @staticmethod
    def encode(obj: Any, schema_type: Optional[type] = None) -> bytes:
        """Encode object to JSON bytes.

        Usage:
            data = MessageSerializer.encode(stock, StockDetailProto)
        """
        if not MSGSPEC_AVAILABLE:
            import json
            return json.dumps(obj, default=str).encode()

        if schema_type:
            encoder = msgspec.json.Encoder(schema_type)
            return encoder.encode(obj)
        else:
            return msgspec.json.encode(obj)

    @staticmethod
    def decode(data: bytes, schema_type: type) -> Any:
        """Decode JSON bytes to object.

        Usage:
            stock = MessageSerializer.decode(json_bytes, StockDetailProto)
        """
        if not MSGSPEC_AVAILABLE:
            import json
            return json.loads(data)

        decoder = msgspec.json.Decoder(schema_type)
        return decoder.decode(data)

    @staticmethod
    def encode_list(items: List[Any], schema_type: type) -> bytes:
        """Encode list of objects."""
        if not MSGSPEC_AVAILABLE:
            import json
            return json.dumps(items, default=str).encode()

        return msgspec.json.encode(items, type=List[schema_type])

    @staticmethod
    def decode_list(data: bytes, schema_type: type) -> List[Any]:
        """Decode JSON bytes to list."""
        if not MSGSPEC_AVAILABLE:
            import json
            return json.loads(data)

        return msgspec.json.decode(data, type=List[schema_type])

    @classmethod
    def benchmark(cls, data: List[Dict], schema_type: type, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark serialization performance.

        Returns:
            {"encode_ms": ..., "decode_ms": ...}
        """
        if not MSGSPEC_AVAILABLE:
            return {"error": "msgspec not available"}

        import time

        # Encode benchmark
        start = time.perf_counter()
        for _ in range(iterations):
            cls.encode_list(data, schema_type)
        encode_time = (time.perf_counter() - start) * 1000 / iterations

        # Decode benchmark
        encoded = cls.encode_list(data, schema_type)
        start = time.perf_counter()
        for _ in range(iterations):
            cls.decode_list(encoded, schema_type)
        decode_time = (time.perf_counter() - start) * 1000 / iterations

        return {
            "encode_ms": encode_time,
            "decode_ms": decode_time,
            "items": len(data)
        }


# Fallback for when msgspec is not available
class FallbackSerializer:
    """Fallback serializer using standard json."""

    @staticmethod
    def encode(obj: Any) -> bytes:
        import json
        return json.dumps(obj, ensure_ascii=False, default=str).encode()

    @staticmethod
    def decode(data: bytes) -> Any:
        import json
        return json.loads(data)


def get_serializer() -> MessageSerializer | FallbackSerializer:
    """Get the appropriate serializer."""
    if MSGSPEC_AVAILABLE:
        return MessageSerializer
    return FallbackSerializer


__all__ = [
    "StockQuoteProto",
    "StockDetailProto", 
    "TradeSignalProto",
    "MarketDataUpdateProto",
    "MessageSerializer",
    "get_serializer",
    "MSGSPEC_AVAILABLE"
]