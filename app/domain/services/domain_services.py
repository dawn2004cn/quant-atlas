from __future__ import annotations
"""Domain Services - Business logic moved from Application layer.

Following Phase 7: Domain Model Purity - these services encapsulate
business rules that were previously scattered in Application Services.
"""


from typing import Any
from datetime import datetime, timedelta

from app.domain.models import RiskCalculator, RiskMetrics, PriceLevel
from app.domain.models import SignalGenerator, TradingSignal, SignalType, SignalDirection, SignalStrength
from app.domain.models import Portfolio, PortfolioAnalyzer, Position, PositionStatus, PositionSide
from app.core.logger import get_logger

logger = get_logger(__name__)


class RiskDomainService:
    """Domain service for risk calculations.
    
    Previously these calculations were embedded in RiskAlertService.
    Now they use pure domain models.
    """

    @staticmethod
    def assess_stock_risk(
        code: str,
        price_history: list[float],
        current_price: float,
        beta: float = 1.0
    ) -> RiskMetrics:
        """Assess risk for a stock using domain models."""
        # Use the RiskCalculator from domain models
        metrics = RiskMetrics.from_price_history(price_history)
        metrics.beta = beta
        
        # Recalculate score with beta
        metrics.score = min(100, metrics.score * (0.7 + beta * 0.3))
        
        # Determine level
        if metrics.score < 25:
            metrics.level = 'low'
        elif metrics.score < 50:
            metrics.level = 'medium'
        elif metrics.score < 75:
            metrics.level = 'high'
        else:
            metrics.level = 'extreme'
            
        return metrics

    @staticmethod
    def calculate_position_risk(
        position: Position,
        portfolio_value: float
    ) -> dict[str, Any]:
        """Calculate risk metrics for a position."""
        position_value = position.total_value()
        weight = position_value / portfolio_value * 100 if portfolio_value > 0 else 0
        
        # Risk contribution to portfolio
        risk_contribution = weight * (position.pnl_pct() / 100)
        
        return {
            'position_value': position_value,
            'weight': weight,
            'pnl': position.pnl(),
            'pnl_pct': position.pnl_pct(),
            'risk_contribution': risk_contribution,
            'holding_days': position.holding_days(),
        }

    @staticmethod
    def find_support_resistance(prices: list[float]) -> dict[str, list[PriceLevel]]:
        """Find support and resistance levels."""
        return RiskCalculator.calculate_support_resistance(prices)


class SignalDomainService:
    """Domain service for signal generation.
    
    Previously embedded in various scanning services.
    """

    @staticmethod
    def generate_signals(
        code: str,
        current_price: float,
        price_history: list[float],
        volume: float,
        avg_volume: float,
        rsi: float | None = None,
        macd: dict | None = None
    ) -> list[TradingSignal]:
        """Generate trading signals using domain models."""
        signals = []
        
        # Breakout signal
        if len(price_history) >= 20:
            high_20d = max(price_history[-20:])
            breakout = SignalGenerator.generate_breakout_signal(
                code, current_price, high_20d, volume, avg_volume
            )
            if breakout:
                signals.append(breakout)

        # Mean reversion signal
        if rsi and len(price_history) >= 20:
            ma_20 = sum(price_history[-20:]) / 20
            bb_lower = ma_20 * 0.95  # Simplified Bollinger
            reversion = SignalGenerator.generate_mean_reversion_signal(
                code, current_price, ma_20, bb_lower, rsi
            )
            if reversion:
                signals.append(reversion)
                
        return signals

    @staticmethod
    def evaluate_signal(signal: TradingSignal) -> dict[str, Any]:
        """Evaluate signal quality."""
        return SignalGenerator.evaluate_signal(signal)


class PortfolioDomainService:
    """Domain service for portfolio operations.
    
    Moved from PortfolioService.
    """

    @staticmethod
    def create_position(
        code: str,
        name: str,
        quantity: int,
        price: float,
        side: str = "long"
    ) -> Position:
        """Create a new position."""
        import uuid
        return Position(
            id=str(uuid.uuid4())[:8],
            code=code,
            name=name,
            quantity=quantity,
            avg_cost=price,
            current_price=price,
            side=PositionSide.LONG if side == "long" else PositionSide.SHORT
        )

    @staticmethod
    def calculate_portfolio_metrics(portfolio: Portfolio) -> dict[str, Any]:
        """Calculate portfolio-level metrics."""
        closed_positions = [p for p in portfolio.positions if p.status == PositionStatus.CLOSED]
        
        return {
            'total_positions': len(portfolio.positions),
            'open_positions': portfolio.position_count(),
            'win_rate': portfolio.win_rate(),
            'sharpe_ratio': PortfolioAnalyzer.calculate_sharpe(portfolio.positions),
            'max_drawdown': PortfolioAnalyzer.calculate_max_drawdown(portfolio.positions),
            'total_pnl': portfolio.total_pnl,
        }

    @staticmethod
    def rebalance_suggestions(
        portfolio: Portfolio,
        target_weights: dict[str, float]
    ) -> list[dict[str, Any]]:
        """Generate rebalancing suggestions."""
        suggestions = []
        
        current_weights = {}
        total_value = sum(p.total_value() for p in portfolio.positions if p.status == PositionStatus.OPEN)
        
        for pos in portfolio.positions:
            if pos.status == PositionStatus.OPEN:
                weight = pos.total_value() / total_value * 100 if total_value > 0 else 0
                current_weights[pos.code] = weight
                
        for code, target in target_weights.items():
            current = current_weights.get(code, 0)
            diff = target - current
            
            if abs(diff) > 5:  # Threshold 5%
                suggestions.append({
                    'code': code,
                    'current_weight': current,
                    'target_weight': target,
                    'action': 'increase' if diff > 0 else 'decrease',
                    'difference': diff
                })
                
        return suggestions


class MarketDomainService:
    """Domain service for market data transformations."""

    @staticmethod
    def normalize_quote(raw_quote: dict) -> dict:
        """Normalize quote from various providers to standard format."""
        return {
            'code': raw_quote.get('code') or raw_quote.get('symbol') or '',
            'name': raw_quote.get('name', ''),
            'price': float(raw_quote.get('price') or raw_quote.get('close') or 0),
            'change': float(raw_quote.get('change') or 0),
            'change_pct': float(raw_quote.get('change_pct') or raw_quote.get('pct_chg') or 0),
            'volume': int(raw_quote.get('volume') or 0),
            'amount': float(raw_quote.get('amount') or 0),
            'high': float(raw_quote.get('high') or 0),
            'low': float(raw_quote.get('low') or 0),
            'open': float(raw_quote.get('open') or 0),
            'prev_close': float(raw_quote.get('prev_close') or raw_quote.get('pre_close') or 0),
        }

    @staticmethod
    def calculate_market_cap(price: float, shares: float) -> float:
        """Calculate market cap in billions."""
        return price * shares / 100000000

    @staticmethod
    def is_trading_time() -> bool:
        """Check if currently in trading hours (CN market)."""
        now = datetime.now()
        
        # Weekend
        if now.weekday() >= 5:
            return False
            
        hour = now.hour
        minute = now.minute
        
        # 9:30-11:30, 13:00-15:00
        if 9 <= hour < 11:
            return minute >= 30
        elif 11 <= hour < 13:
            return False
        elif 13 <= hour < 15:
            return True
            
        return False