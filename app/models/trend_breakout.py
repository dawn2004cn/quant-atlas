"""
Facade for trend breakout strategies.

This module re-exports all strategy classes from `trend_breakout_model.py`
for backward compatibility.

## Split structure (God Class refactor):
- trend_breakout_model.py  -- 24 pure computation strategy classes (model layer)
- trend_breakout_service.py -- CANSLIMService + TrendBreakoutService (service layer)
- trend_breakout.py (this file) -- facade preserving original import paths
"""

from __future__ import annotations

from .trend_breakout_model import (
    MAStrategy,
    DualMovingAverageStrategy,
    MultiMAResonanceStrategy,
    LotusOutWaterStrategy,
    MASqueezeBreakoutStrategy,
    EMAMACDContinuationStrategy,
    MACDZeroCrossStrategy,
    DMITrendStrategy,
    VolumeBreakoutStrategy,
    VolBBBreakoutStrategy,
    VolMABreakoutStrategy,
    ThreeWhiteSoldiersStrategy,
    TAUStrategy,
    NR7BreakoutStrategy,
    TTMSqueezeBreakoutStrategy,
    TurtleTradingStrategy,
    GuppyMMAStrategy,
    IchimokuCloudStrategy,
    BBSqueezeStrategy,
    ATRExpansionStrategy,
    ChandelierExitStrategy,
    AlligatorAwakeningStrategy,
    CANSLIMModelStrategy,
)

from .trend_breakout_service import CANSLIMService, TrendBreakoutService

__all__ = [
    # -- 24 strategy classes (pure model) --
    "MAStrategy",
    "DualMovingAverageStrategy",
    "MultiMAResonanceStrategy",
    "LotusOutWaterStrategy",
    "MASqueezeBreakoutStrategy",
    "EMAMACDContinuationStrategy",
    "MACDZeroCrossStrategy",
    "DMITrendStrategy",
    "VolumeBreakoutStrategy",
    "VolBBBreakoutStrategy",
    "VolMABreakoutStrategy",
    "ThreeWhiteSoldiersStrategy",
    "TAUStrategy",
    "NR7BreakoutStrategy",
    "TTMSqueezeBreakoutStrategy",
    "TurtleTradingStrategy",
    "GuppyMMAStrategy",
    "IchimokuCloudStrategy",
    "BBSqueezeStrategy",
    "ATRExpansionStrategy",
    "ChandelierExitStrategy",
    "AlligatorAwakeningStrategy",
    "CANSLIMModelStrategy",
    # -- 2 service classes --
    "CANSLIMService",
    "TrendBreakoutService",
]