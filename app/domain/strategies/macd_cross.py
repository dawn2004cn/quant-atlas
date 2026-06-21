from .base import BaseStrategy, StrategySignal, StrategyResult


def _compute_macd(prices: list[float], period: int = 12) -> tuple[float, float, float]:
    if len(prices) < period + 9:
        return 0.0, 0.0, 0.0
    ema_fast = sum(prices[-period:]) / period
    ema_slow = sum(prices[-period * 2:]) / (period * 2) if len(prices) >= period * 2 else ema_fast
    macd = ema_fast - ema_slow
    signal = macd
    hist = macd - signal
    return macd, signal, hist


class MacdCrossStrategy(BaseStrategy):
    """Straightforward MACD-cross strategy expecting settings: qty, period."""

    def analyze(self, data: dict) -> StrategyResult:
        price = data.get("price", 0)
        prices = data.get("prices", [price])
        period = self.params.get("period", 12)
        macd, signal, hist = _compute_macd(prices, period=period)
        signals = []
        if macd > signal and hist < 0:
            signals.append(StrategySignal(
                code=data.get("symbol", ""),
                direction="long",
                strength=0.7,
                price=price,
                reason="MACD bullish cross",
            ))
        if macd < signal and hist > 0:
            signals.append(StrategySignal(
                code=data.get("symbol", ""),
                direction="short",
                strength=0.7,
                price=price,
                reason="MACD bearish cross",
            ))
        return StrategyResult(signals=signals)

    def on_market_tick(self, market_data: dict) -> list[StrategySignal]:
        result = self.analyze(market_data)
        return result.signals
