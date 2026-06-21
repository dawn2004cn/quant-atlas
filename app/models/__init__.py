from __future__ import annotations
"""
Unified strategy registry and accessor.
Updated to support parameterization via StrategyFactory.
"""


from typing import Any

from ..core.factory import StrategyFactory
from ..domain.entities import StrategyConfig

# ==========================================
# 📈 1. 趋势突破与动量成长
# ==========================================
from .trend_breakout import (
    MAStrategy, MultiMAResonanceStrategy, LotusOutWaterStrategy,
    MASqueezeBreakoutStrategy, EMAMACDContinuationStrategy, MACDZeroCrossStrategy,
    DMITrendStrategy, VolumeBreakoutStrategy, VolBBBreakoutStrategy,
    VolMABreakoutStrategy, ThreeWhiteSoldiersStrategy, TAUStrategy,
    NR7BreakoutStrategy, TTMSqueezeBreakoutStrategy, TurtleTradingStrategy,
    GuppyMMAStrategy, IchimokuCloudStrategy, BBSqueezeStrategy,
    ATRExpansionStrategy, ChandelierExitStrategy, AlligatorAwakeningStrategy,
    CANSLIMModelStrategy, DualMovingAverageStrategy
)

# 注册趋势突破类
_TREND_MAP = {
    "MA": MAStrategy, "MultiMA": MultiMAResonanceStrategy, "Lotus": LotusOutWaterStrategy,
    "MASqueeze": MASqueezeBreakoutStrategy, "EMAMACD": EMAMACDContinuationStrategy,
    "MACDZero": MACDZeroCrossStrategy, "DMI": DMITrendStrategy, "VolBreak": VolumeBreakoutStrategy,
    "VolBB": VolBBBreakoutStrategy, "VolMA": VolMABreakoutStrategy, "ThreeSoldiers": ThreeWhiteSoldiersStrategy,
    "TAU": TAUStrategy, "NR7": NR7BreakoutStrategy, "TTM": TTMSqueezeBreakoutStrategy,
    "Turtle": TurtleTradingStrategy, "Guppy": GuppyMMAStrategy, "Ichimoku": IchimokuCloudStrategy,
    "BBSqueeze": BBSqueezeStrategy, "ATR": ATRExpansionStrategy, "Chandelier": ChandelierExitStrategy,
    "Alligator": AlligatorAwakeningStrategy, "CANSLIM": CANSLIMModelStrategy, "DualMA": DualMovingAverageStrategy
}

# ==========================================
# ⚖️ 2. 均值回归与震荡波段
# ==========================================
from .mean_reversion import (
    ChannelPullbackStrategy, SingleBullishHoldStrategy, BollingerRSIReversionStrategy,
    BBRSIReversionStrategy, RSIStrategy, StochasticSwingStrategy,
    BIASPanicStrategy, BBLowerSupportStrategy, ConnorsRSI2Strategy,
    ZScoreMeanReversionStrategy, CCITurningStrategy
)
from .oscillation import KDJSwingStrategy

_MEAN_REV_MAP = {
    "ChannelPullback": ChannelPullbackStrategy, "SingleBullish": SingleBullishHoldStrategy,
    "BollingerRSI": BollingerRSIReversionStrategy, "BBRSI": BBRSIReversionStrategy,
    "RSI": RSIStrategy, "StochSwing": StochasticSwingStrategy, "BIAS": BIASPanicStrategy,
    "BBLower": BBLowerSupportStrategy, "ConnorsRSI2": ConnorsRSI2Strategy,
    "ZScore": ZScoreMeanReversionStrategy, "CCI": CCITurningStrategy, "KDJSwing": KDJSwingStrategy
}

# ==========================================
# 🩸 3. 恐慌抄底与极值反转
# ==========================================
from .panic_bottom import (
    MACDBottomCrossStrategy, MACDDivergenceStrategy, KDJGoldenPitStrategy,
    RSIReversalStrategy, TDXPrecisionStrategy, Sperandeo2BReversalStrategy,
    TDSequentialSetupStrategy, WyckoffSpringStrategy
)

_PANIC_MAP = {
    "MACDBottom": MACDBottomCrossStrategy, "MACDDiverge": MACDDivergenceStrategy,
    "KDJGolden": KDJGoldenPitStrategy, "RSIRev": RSIReversalStrategy,
    "TDXPrecision": TDXPrecisionStrategy, "Sperandeo2B": Sperandeo2BReversalStrategy,
    "TD9": TDSequentialSetupStrategy, "Wyckoff": WyckoffSpringStrategy
}

# ==========================================
# 🏢 4. 机构资金与动量回调
# ==========================================
from .institutional import (
    OBVAccumulationStrategy, VPTDivergenceStrategy, StrongTrendDipStrategy,
    MinerviniVCPStrategy, RaschkeHolyGrailStrategy, ElderImpulseStrategy,
    VWAPPullbackStrategy, ChaikinMoneyFlowStrategy, ChoppinessIndexStrategy
)

# ==========================================
# 🧠 5. Qlib 高胜率（脚本移植，轻量版）
# ==========================================
from .qlib_high_win import build_qlib_high_win_registry
from .extended_28 import build_extended_28_registry

_INSTITUTIONAL_MAP = {
    "OBV": OBVAccumulationStrategy, "VPT": VPTDivergenceStrategy, "StrongDip": StrongTrendDipStrategy,
    "VCP": MinerviniVCPStrategy, "HolyGrail": RaschkeHolyGrailStrategy,
    "Impulse": ElderImpulseStrategy, "VWAP": VWAPPullbackStrategy,
    "CMF": ChaikinMoneyFlowStrategy, "Chop": ChoppinessIndexStrategy
}

# Qlib 高胜率注册表（strategy_id 以 QHW 前缀区分）
_QLIB_HIGH_WIN_MAP = build_qlib_high_win_registry()
_EXTENDED_28_MAP = build_extended_28_registry()

# 自动注册到工厂
for mapper in [_TREND_MAP, _MEAN_REV_MAP, _PANIC_MAP, _INSTITUTIONAL_MAP, _QLIB_HIGH_WIN_MAP, _EXTENDED_28_MAP]:
    for sid, scls in mapper.items():
        StrategyFactory.register(sid, scls)

# 为了兼容旧代码，提供默认实例列表
TREND_BREAKOUT_MODELS = [scls() for scls in _TREND_MAP.values()]
MEAN_REVERSION_MODELS = [scls() for scls in _MEAN_REV_MAP.values()]
PANIC_BOTTOM_MODELS = [scls() for scls in _PANIC_MAP.values()]
INSTITUTIONAL_MODELS = [scls() for scls in _INSTITUTIONAL_MAP.values()]

ALL_STRATEGIES = (
    TREND_BREAKOUT_MODELS +
    MEAN_REVERSION_MODELS +
    PANIC_BOTTOM_MODELS +
    INSTITUTIONAL_MODELS +
    [scls() for scls in _QLIB_HIGH_WIN_MAP.values()] +
    [scls() for scls in _EXTENDED_28_MAP.values()]
)

# 回测页分组下拉：value 为注册键，与 ``DefaultBacktestProvider.run`` 名称匹配逻辑一致
STRATEGY_REGISTRY_GROUPS: tuple[dict[str, Any], ...] = (
    {
        "id": "trend_breakout",
        "title": "趋势突破与动量成长",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _TREND_MAP.items()),
    },
    {
        "id": "mean_reversion",
        "title": "均值回归与震荡波段",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _MEAN_REV_MAP.items()),
    },
    {
        "id": "panic_bottom",
        "title": "恐慌抄底与极值反转",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _PANIC_MAP.items()),
    },
    {
        "id": "institutional",
        "title": "机构资金与动量回调",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _INSTITUTIONAL_MAP.items()),
    },
    {
        "id": "qlib_high_win",
        "title": "Qlib 高胜率（脚本移植·轻量版）",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _QLIB_HIGH_WIN_MAP.items()),
    },
    {
        "id": "extended_28",
        "title": "扩展策略库（新增 28）",
        "items": tuple({"key": k, "label": cls().name} for k, cls in _EXTENDED_28_MAP.items()),
    },
)

__all__ = [
    'TREND_BREAKOUT_MODELS',
    'MEAN_REVERSION_MODELS',
    'PANIC_BOTTOM_MODELS',
    'INSTITUTIONAL_MODELS',
    'ALL_STRATEGIES',
    'STRATEGY_REGISTRY_GROUPS',
    'StrategyFactory'
]
