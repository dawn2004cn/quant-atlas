from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .runtime_config import get_runtime, get_runtime_float, get_runtime_int


@dataclass(frozen=True)
class RiskControlParams:
    """全局风控默认参数：用于回测/信号扫描的统一后处理。"""

    stop_loss_pct: float = -0.08
    take_profit_pct: float = 0.10
    vol_ma_window: int = 10
    vol_ratio_min: float = 1.2
    volat_window: int = 20
    volat_min: float = 0.01
    atr_window: int = 14
    atr_mult: float = 3.0
    trailing_atr: bool = True
    sentiment_gate: bool = True
    sentiment_min_score: float = 50.0
    #: 是否在**历史回测**中应用逐日情绪门（见 ``DefaultBacktestProvider._cn_sentiment_for_trade_date``）。
    backtest_sentiment_gate: bool = True
    #: A 股涨跌停/停牌/一字板近似约束（日频回测）。
    apply_cn_price_limits: bool = True


@dataclass(frozen=True)
class TradeCostParams:
    """交易成本（统一回测）默认参数。"""

    open_commission: float = 0.0003
    close_commission: float = 0.0003
    stamp_duty: float = 0.00025  # A 股卖出印花税（2023-08-28 起万2.5）
    slippage_bps: float = 8.0  # 单边滑点（bps）
    min_fee: float = 5.0
    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.00025
    transfer_fee: float = 0.00002  # 过户费万2双边
    apply_cash_dividends: bool = True  # 未复权行情 + Dividend 列时计入现金分红


@dataclass(frozen=True)
class PositionSizingParams:
    """仓位管理参数（统一回测）。"""

    mode: str = "hybrid"  # full/max_weight/risk/hybrid
    max_weight: float = 0.2
    risk_per_trade: float = 0.01
    cn_lot_size: int = 100
    max_positions: int = 5
    limit_threshold: float = 0.095


def load_default_risk_params() -> RiskControlParams:
    """从运行时配置加载全局风控参数（config.cfg / env）。"""
    return RiskControlParams(
        stop_loss_pct=get_runtime_float("RISK_STOP_LOSS_PCT", -0.08),
        take_profit_pct=get_runtime_float("RISK_TAKE_PROFIT_PCT", 0.10),
        vol_ma_window=get_runtime_int("RISK_VOL_MA_WINDOW", 10),
        vol_ratio_min=get_runtime_float("RISK_VOL_RATIO_MIN", 1.2),
        volat_window=get_runtime_int("RISK_VOLAT_WINDOW", 20),
        volat_min=get_runtime_float("RISK_VOLAT_MIN", 0.01),
        atr_window=get_runtime_int("RISK_ATR_WINDOW", 14),
        atr_mult=get_runtime_float("RISK_ATR_MULT", 3.0),
        trailing_atr=(str(get_runtime_int("RISK_TRAILING_ATR", 1)).strip() != "0"),
        sentiment_gate=(str(get_runtime_int("RISK_SENTIMENT_GATE", 1)).strip() != "0"),
        sentiment_min_score=get_runtime_float("RISK_SENTIMENT_MIN_SCORE", 50.0),
        backtest_sentiment_gate=(str(get_runtime_int("RISK_BACKTEST_SENTIMENT_GATE", 1)).strip() != "0"),
        apply_cn_price_limits=(str(get_runtime_int("BT_APPLY_CN_LIMITS", 1)).strip() != "0"),
    )


def load_default_trade_cost_params() -> TradeCostParams:
    """从运行时配置加载交易成本参数（config.cfg / env）。"""
    stamp = get_runtime_float("BT_STAMP_DUTY", 0.00025)
    return TradeCostParams(
        open_commission=get_runtime_float("BT_OPEN_COMMISSION", 0.0003),
        close_commission=get_runtime_float("BT_CLOSE_COMMISSION", 0.0003),
        stamp_duty=stamp,
        slippage_bps=get_runtime_float("BT_SLIPPAGE_BPS", 8.0),
        min_fee=get_runtime_float("BT_MIN_FEE", 5.0),
        commission_rate=get_runtime_float("BT_COMMISSION_RATE", 0.0003),
        stamp_tax_rate=get_runtime_float("BT_STAMP_TAX_RATE", stamp),
        transfer_fee=get_runtime_float("BT_TRANSFER_FEE", 0.00002),
        apply_cash_dividends=(str(get_runtime_int("BT_APPLY_CASH_DIVIDENDS", 1)).strip() != "0"),
    )


def load_default_position_sizing_params() -> PositionSizingParams:
    """从运行时配置加载仓位管理参数（config.cfg / env）。"""
    return PositionSizingParams(
        mode=(get_runtime("BT_POSITION_SIZING_MODE", "hybrid") or "hybrid").strip().lower(),
        max_weight=get_runtime_float("BT_MAX_WEIGHT", 0.2),
        risk_per_trade=get_runtime_float("BT_RISK_PER_TRADE", 0.01),
        cn_lot_size=get_runtime_int("BT_CN_LOT_SIZE", 100),
        max_positions=get_runtime_int("BT_MAX_POSITIONS", 5),
        limit_threshold=get_runtime_float("BT_LIMIT_THRESHOLD", 0.095),
    )


def _safe_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def compute_liquidity_filters(df: pd.DataFrame, *, p: RiskControlParams | None = None) -> pd.Series:
    """成交量过滤 + 波动率过滤。

    返回与 df 同长度的布尔序列：True 表示“允许开仓买入”。
    """
    p = p or load_default_risk_params()
    if df.empty:
        return pd.Series([], dtype=bool)
    if "Close" not in df.columns or "Volume" not in df.columns:
        return pd.Series([False] * len(df), index=df.index, dtype=bool)

    close = _safe_num(df["Close"])
    vol = _safe_num(df["Volume"])
    vol_ma = vol.rolling(int(p.vol_ma_window)).mean()
    vol_ok = vol > (vol_ma * float(p.vol_ratio_min))

    volat = close.pct_change().rolling(int(p.volat_window)).std()
    volat_ok = volat > float(p.volat_min)

    out = (vol_ok.fillna(False)) & (volat_ok.fillna(False))
    return out.astype(bool)


def compute_atr(df: pd.DataFrame, *, window: int = 14) -> pd.Series:
    """计算 ATR（Wilder RMA 平滑），要求 High/Low/Close 列存在。"""
    if df.empty or not {"High", "Low", "Close"}.issubset(set(df.columns)):
        return pd.Series([np.nan] * len(df), index=df.index)
    high = _safe_num(df["High"])
    low = _safe_num(df["Low"])
    close = _safe_num(df["Close"])
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            (high - low).abs(),
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    win = int(window)
    return tr.ewm(alpha=1.0 / win, min_periods=win, adjust=False).mean()


def round_shares_for_market(shares: int, *, market: str, lot_size_cn: int = 100) -> int:
    """按交易所股数规则向下取整，尽量避免零散股数。"""
    n = int(shares or 0)
    if n <= 0:
        return 0
    m = (market or "").strip().upper()
    if m in ("CN", "A", "ASHARE", "A_SHARE"):
        lot = max(1, int(lot_size_cn or 100))
        return (n // lot) * lot
    return n

