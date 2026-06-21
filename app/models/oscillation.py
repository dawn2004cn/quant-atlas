import pandas as pd
import numpy as np
from ..core.base_strategy import BaseTradingStrategy
from ta.momentum import StochasticOscillator
from ..core.kdj import tdx_k_d


class KDJSwingStrategy(BaseTradingStrategy):
    """策略 16: KDJ 波段超卖金叉"""

    @property
    def name(self) -> str: return "16. KDJ 波段金叉"

    @property
    def category(self) -> str: return "震荡波段"

    @property
    def description(self) -> str: return "KDJ指标的K值在30以下的超卖区，向上穿越D值形成黄金交叉。"

    @property
    def principle(self) -> str: return "震荡市短线转折。过滤掉中高位的无效交叉，只在短线情绪最绝望的底部捕捉买盘资金入场带来的短波段反弹利润。"

    def get_start_idx(self) -> int: return 15

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        stoch = StochasticOscillator(df['High'], df['Low'], df['Close'], 9, 3)
        k, d = tdx_k_d(stoch)
        df['Signal'] = 0

        buy_cond = (k > d) & (k.shift(1) <= d.shift(1)) & (k.shift(1) < 30)
        sell_cond = (k < d) & (k.shift(1) >= d.shift(1)) & (k.shift(1) > 70)
        df.loc[buy_cond, 'Signal'] = 1
        df.loc[sell_cond, 'Signal'] = -1
        return df
