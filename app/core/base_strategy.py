from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import pandas as pd


# ─── Transaction cost model ────────────────────────────────────────────


@dataclass
class TransactionCostConfig:
    """Transaction cost parameters that strategies can query to assess cost-awareness.

    All values are ratios (e.g. 0.001 = 0.1%). Designed to mirror
    ``TradeCostParams`` in ``core.risk_controls``.

    Attributes:
        commission_rate: One-side commission ratio (buy + sell).
        stamp_tax_rate: Sell-side stamp tax ratio (A-share only).
        slippage_bps: Slippage in basis points (one side).
        transfer_fee: Transfer fee ratio (both sides, A-share).
        min_fee: Minimum commission per trade (yuan).
    """

    commission_rate: float = 0.0003
    stamp_tax_rate: float = 0.00025
    slippage_bps: float = 8.0
    transfer_fee: float = 0.00002
    min_fee: float = 5.0

    @property
    def round_trip_cost_bps(self) -> float:
        """Estimated total cost for a round trip (open + close) in bps."""
        round_trip = (
            self.commission_rate * 2          # open comm + close comm
            + self.stamp_tax_rate              # sell-side stamp tax
            + self.transfer_fee * 2            # transfer fee both sides
            + self.slippage_bps * 2 / 10000    # slippage both sides
        )
        return round_trip * 10000  # return in bps

    def estimate_one_way_cost(self, notional: float, is_buy: bool = True) -> float:
        """Estimate cost for a single trade direction."""
        comm = max(notional * self.commission_rate, self.min_fee)
        comm += notional * self.transfer_fee
        if not is_buy:
            comm += notional * self.stamp_tax_rate
        slippage = notional * self.slippage_bps / 10000
        return comm + slippage


# ─── Base strategy interface ───────────────────────────────────────────


class BaseTradingStrategy(ABC):
    """
    交易策略抽象基类。
    所有具体的交易策略都必须继承该类并实现 generate_signals 方法。
    """

    #: Transaction cost config attached at factory-creation time.
    #: Subclasses can query ``self.transaction_cost`` to assess whether
    #: a signal's expected profit exceeds the cost floor.
    transaction_cost: TransactionCostConfig = field(default_factory=TransactionCostConfig)

    def __post_init__(self) -> None:
        """Hook for subclasses that use dataclass __post_init__."""
        pass

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    @abstractmethod
    def category(self) -> str:
        """策略分类：趋势突破 / 均值回归 / 震荡波段 / 恐慌抄底 / 机构资金"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """给交易员的策略简述"""
        pass

    @property
    @abstractmethod
    def principle(self) -> str:
        """底层金融学与行为学原理"""
        pass

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        根据历史数据生成买卖信号
        :param df: 包含 Open, High, Low, Close, Volume 的 DataFrame
        :return: 带有 'Signal' 列的 DataFrame (1: 买入, -1: 卖出, 0: 观望)
        """
        pass

    @abstractmethod
    def get_start_idx(self) -> int:
        """获取策略开始索引"""
        pass

    def estimated_roundtrip_cost_bps(self) -> float:
        """Return the estimated round-trip cost in basis points.

        Subclasses can override to use market-specific costs.
        Default delegates to the attached ``TransactionCostConfig``.
        """
        return self.transaction_cost.round_trip_cost_bps

    def horizon_tags(self) -> list[str]:
        """
        返回该策略适用的时间维度标签。
        - short:  超短/短线 ~ 数日~数周持仓（适合日内、隔夜、趋势初期）
        - mid:    中线 ~ 数周~数月持仓（适合趋势中期、波段操作）
        - long:   长线 ~ 数月~数年持仓（适合长线）

        子类可覆盖；默认按 get_start_idx 推断。
        推断依据：缓存提供约 220 交易日数据。
        - short:  快速反应型，get_start_idx <= 35（适合短线）
        - mid:    标准型，36 <= get_start_idx <= 120（适合中线）
        - long:   长期型，get_start_idx > 120（适合长线）
        其中 mid 与 long 互不包含，保证筛选结果互不重叠。
        """
        bars = self.get_start_idx()
        if bars <= 35:
            return ["short", "mid"]
        if bars <= 120:
            return ["mid"]
        return ["long"]
