from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, SMAIndicator
from ta.volatility import BollingerBands

from ..core.base_strategy import BaseTradingStrategy


def _volatility(close: pd.Series, window: int) -> pd.Series:
    return close.pct_change().rolling(window).std()


def _safe_series(df: pd.DataFrame, name: str) -> pd.Series:
    if name not in df.columns:
        return pd.Series([np.nan] * len(df), index=df.index)
    return pd.to_numeric(df[name], errors="coerce")


@dataclass(frozen=True)
class QlibHighWinParams:
    """轻量版“Qlib 高胜率策略”参数（适配本平台回测引擎的单标的信号输出）。"""

    stop_loss_pct: float = -0.08
    vol_ma_window: int = 10
    vol_ratio_min: float = 1.2
    volat_window: int = 20
    volat_min: float = 0.01


class QlibHighWinBaseStrategy(BaseTradingStrategy):
    """将脚本版 Qlib 规则策略移植为平台 `BaseTradingStrategy`（不依赖 pyqlib）。"""

    def __init__(self, *, params: QlibHighWinParams | None = None):
        self._p = params or QlibHighWinParams()

    @property
    def category(self) -> str:
        return "Qlib 高胜率（规则/轻量）"

    @property
    def principle(self) -> str:
        return "波动率与成交量过滤降低噪声；用均值回归/动量信号寻找高赔率入场，辅以硬止损控制尾部风险。"

    def get_start_idx(self) -> int:
        return 60

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = _safe_series(out, "Close")
        vol = _safe_series(out, "Volume")

        out["rsi14"] = RSIIndicator(close, window=14).rsi()
        ema12 = EMAIndicator(close, window=12).ema_indicator()
        ema26 = EMAIndicator(close, window=26).ema_indicator()
        out["macd"] = ema12 - ema26
        out["macd_signal"] = EMAIndicator(out["macd"], window=9).ema_indicator()
        out["macd_hist"] = out["macd"] - out["macd_signal"]

        bb = BollingerBands(close, window=20, window_dev=2)
        out["bb_mid"] = bb.bollinger_mavg()
        out["bb_upper"] = bb.bollinger_hband()
        out["bb_lower"] = bb.bollinger_lband()

        out["ma_short"] = SMAIndicator(close, window=5).sma_indicator()
        out["ma_long"] = SMAIndicator(close, window=20).sma_indicator()
        out["vol_ma"] = vol.rolling(self._p.vol_ma_window).mean()
        out["volatility"] = _volatility(close, self._p.volat_window)
        return out

    def _passes_liquidity_filters(self, df: pd.DataFrame) -> pd.Series:
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df.get("vol_ma"), errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        volat = pd.to_numeric(df.get("volatility"), errors="coerce")
        volat_ok = volat > float(self._p.volat_min)
        return (vol_ok.fillna(False)) & (volat_ok.fillna(False))

    def _apply_stop_loss(self, df: pd.DataFrame, signals: pd.Series) -> pd.Series:
        """按持仓状态生成止损卖出信号（与平台回测引擎的“单仓位”假设对齐）。"""
        close = _safe_series(df, "Close")
        stop = float(self._p.stop_loss_pct)
        out = signals.copy()
        in_pos = False
        entry = 0.0
        for i in range(len(df)):
            sig = int(out.iat[i]) if pd.notna(out.iat[i]) else 0
            px = float(close.iat[i]) if pd.notna(close.iat[i]) else 0.0
            if not in_pos and sig == 1 and px > 0:
                in_pos = True
                entry = px
                continue
            if in_pos and px > 0 and entry > 0:
                if (px / entry) - 1.0 < stop:
                    out.iat[i] = -1
                    in_pos = False
                    entry = 0.0
                    continue
            if in_pos and sig == -1:
                in_pos = False
                entry = 0.0
        return out

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self._enrich(df)
        out["Signal"] = 0
        base = self._rule_signals(out).fillna(0).astype(int)
        base = self._apply_stop_loss(out, base)
        out["Signal"] = base
        return out


class QHW01_RSI_MeanReversion(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW01. RSI 均值回归（量能+波动过滤/止损）"

    @property
    def description(self) -> str:
        return "RSI<30 视为超卖，配合放量与波动过滤入场；RSI>70 退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        buy = (rsi < 30) & filt
        sell = rsi > 70
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW02_Bollinger_MeanReversion(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW02. 布林下轨回归（量能+波动过滤/止损）"

    @property
    def description(self) -> str:
        return "收盘跌破布林下轨且过滤通过则入场；上破上轨或止损退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        close = _safe_series(df, "Close")
        buy = (close < pd.to_numeric(df["bb_lower"], errors="coerce")) & filt
        sell = close > pd.to_numeric(df["bb_upper"], errors="coerce")
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW03_MACD_Crossover(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW03. MACD 多头切换（量能过滤/止损）"

    @property
    def description(self) -> str:
        return "MACD 柱>0 且 DIF>DEA 视为多头；弱化后退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        macd_hist = pd.to_numeric(df["macd_hist"], errors="coerce")
        macd = pd.to_numeric(df["macd"], errors="coerce")
        sigl = pd.to_numeric(df["macd_signal"], errors="coerce")
        buy = (macd_hist > 0) & (macd > sigl) & vol_ok.fillna(False)
        sell = (macd_hist < 0) & (macd < sigl)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW04_MA_GoldenCross(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW04. 均线金叉（量能+波动过滤/止损）"

    @property
    def description(self) -> str:
        return "短期 MA>长期 MA 且过滤通过则做多；跌回长期均线下方退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        ma_s = pd.to_numeric(df["ma_short"], errors="coerce")
        ma_l = pd.to_numeric(df["ma_long"], errors="coerce")
        close = _safe_series(df, "Close")
        buy = (ma_s > ma_l) & filt
        sell = close < ma_l
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW05_Stochastic_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW05. 超卖摆动（RSI 近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中使用随机指标，这里用 RSI<20 近似超卖入场，RSI>80 退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        buy = (rsi < 20) & vol_ok.fillna(False)
        sell = rsi > 80
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW06_CCI_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW06. CCI 回归（RSI 近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中的 CCI 类策略，这里用 RSI<25 近似入场，RSI>75 退出。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        buy = (rsi < 25) & vol_ok.fillna(False)
        sell = rsi > 75
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW07_KDJ_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW07. KDJ 金叉（RSI 近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中 KDJ，这里用 RSI<30 + 放量近似金叉吸筹入场。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        buy = (rsi < 30) & vol_ok.fillna(False)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        return sig


class QHW08_WilliamsR_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW08. 威廉超卖（RSI 近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中 Williams%R，这里用 RSI<20/RSI>80 近似实现。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * float(self._p.vol_ratio_min))
        buy = (rsi < 20) & vol_ok.fillna(False)
        sell = rsi > 80
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy] = 1
        sig.loc[sell] = -1
        return sig


class QHW09_RSI_MACD_Resonance(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW09. RSI+MACD 共振（量能过滤/止损）"

    @property
    def description(self) -> str:
        return "RSI<35 且 MACD 柱>0 并放量，则视为低位转强共振做多。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        mh = pd.to_numeric(df["macd_hist"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        buy = (rsi < 35) & (mh > 0) & (vol > vol_ma * float(self._p.vol_ratio_min))
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        return sig


class QHW10_BB_RSI_Volume(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW10. BB+RSI+量能（波动过滤/止损）"

    @property
    def description(self) -> str:
        return "收盘<下轨 + RSI<30 + 放量（阈值更高）+ 波动过滤 → 逆势回归做多。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        close = _safe_series(df, "Close")
        bb_l = pd.to_numeric(df["bb_lower"], errors="coerce")
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        volat = pd.to_numeric(df["volatility"], errors="coerce")
        buy = (close < bb_l) & (rsi < 30) & (vol > vol_ma * 1.5) & (volat > float(self._p.volat_min))
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        return sig


class QHW11_Alpha158_LiteRank(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW11. Alpha158 轻量因子排序（无训练/止损）"

    @property
    def description(self) -> str:
        return "用收益动量、波动率、均线斜率构造轻量综合分；分数转正且过滤通过做多。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        close = _safe_series(df, "Close")
        ret20 = close.pct_change(20)
        volat = pd.to_numeric(df["volatility"], errors="coerce")
        slope = pd.to_numeric(df["ma_long"], errors="coerce").pct_change(10)
        score = (ret20.rank(pct=True) * 0.45) + ((-volat).rank(pct=True) * 0.35) + (slope.rank(pct=True) * 0.20)
        buy = (score > 0.7) & filt
        sell = score < 0.45
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW12_DoubleEnsemble_Lite(QHW11_Alpha158_LiteRank):
    @property
    def name(self) -> str:
        return "QHW12. DoubleEnsemble 轻量版（无训练/止损）"

    @property
    def description(self) -> str:
        return "在 QHW11 的基础上叠加 MACD 动量过滤，提高顺势胜率。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        base = super()._rule_signals(df)
        mh = pd.to_numeric(df["macd_hist"], errors="coerce")
        base = base.where(mh.fillna(0) > -0.02, other=0)
        return base


class QHW13_XGBoost_Lite(QHW11_Alpha158_LiteRank):
    @property
    def name(self) -> str:
        return "QHW13. XGBoost 轻量版（无训练/止损）"

    @property
    def description(self) -> str:
        return "强调波动率收敛 + 均线金叉的组合，偏稳健趋势启动。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        volat = pd.to_numeric(df["volatility"], errors="coerce")
        ma_s = pd.to_numeric(df["ma_short"], errors="coerce")
        ma_l = pd.to_numeric(df["ma_long"], errors="coerce")
        macd_hist = pd.to_numeric(df["macd_hist"], errors="coerce")
        buy = (volat < volat.rolling(60).quantile(0.35)) & (ma_s > ma_l) & (macd_hist > 0) & filt
        sell = (ma_s < ma_l) | (macd_hist < 0)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW14_RandomForest_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW14. RandomForest 轻量版（无训练/止损）"

    @property
    def description(self) -> str:
        return "用 z-score（20日）识别极端偏离并回归，适配震荡市。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        close = _safe_series(df, "Close")
        mu = close.rolling(20).mean()
        sd = close.rolling(20).std()
        z = (close - mu) / sd.replace(0, np.nan)
        buy = (z < -1.8) & filt
        sell = z > -0.2
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW15_FactorRank_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW15. 因子 Rank 轻量版（无训练/止损）"

    @property
    def description(self) -> str:
        return "综合（低 RSI、布林下轨偏离、放量）打分，分位数较高时做多。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        close = _safe_series(df, "Close")
        bb_l = pd.to_numeric(df["bb_lower"], errors="coerce")
        rsi = pd.to_numeric(df["rsi14"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        score = ((bb_l - close).rank(pct=True) * 0.45) + ((30 - rsi).rank(pct=True) * 0.35) + (
            (vol / vol_ma.replace(0, np.nan)).rank(pct=True) * 0.20
        )
        buy = (score > 0.72) & filt
        sell = score < 0.48
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW16_HF_RSI_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW16. 高频 RSI（轻量近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中为 1min 策略；平台按日线回测时用 RSI(6) 近似，适合短周期震荡。"

    def get_start_idx(self) -> int:
        return 20

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = _safe_series(out, "Close")
        vol = _safe_series(out, "Volume")
        out["rsi6"] = RSIIndicator(close, window=6).rsi()
        out["vol_ma"] = vol.rolling(max(5, self._p.vol_ma_window // 2)).mean()
        out["volatility"] = _volatility(close, window=10)
        return out

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        rsi = pd.to_numeric(df["rsi6"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        vol_ok = vol > (vol_ma * 1.15)
        buy = (rsi < 18) & vol_ok.fillna(False)
        sell = rsi > 78
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW17_HF_MACD_Lite(QHW16_HF_RSI_Lite):
    @property
    def name(self) -> str:
        return "QHW17. 高频 MACD（轻量近似/止损）"

    @property
    def description(self) -> str:
        return "脚本中为 1min；这里用 MACD(6,13,5) 的柱体翻正近似短周期动量。"

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = _safe_series(out, "Close")
        vol = _safe_series(out, "Volume")
        ema6 = EMAIndicator(close, window=6).ema_indicator()
        ema13 = EMAIndicator(close, window=13).ema_indicator()
        out["macd"] = ema6 - ema13
        out["macd_signal"] = EMAIndicator(out["macd"], window=5).ema_indicator()
        out["macd_hist"] = out["macd"] - out["macd_signal"]
        out["vol_ma"] = vol.rolling(max(5, self._p.vol_ma_window // 2)).mean()
        out["volatility"] = _volatility(close, window=10)
        return out

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        mh = pd.to_numeric(df["macd_hist"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        buy = (mh > 0) & (vol > vol_ma * 1.1)
        sell = mh < 0
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW18_HF_Momentum_Lite(QHW16_HF_RSI_Lite):
    @property
    def name(self) -> str:
        return "QHW18. 高频动量（轻量近似/止损）"

    @property
    def description(self) -> str:
        return "用 5 日收益动量 + 放量过滤近似 1min 动量策略；适合趋势加速阶段。"

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        close = _safe_series(df, "Close")
        mom = close.pct_change(5)
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        buy = (mom > mom.rolling(60).quantile(0.7)) & (vol > vol_ma * 1.1)
        sell = mom < mom.rolling(60).quantile(0.3)
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW19_HF_BB_Lite(QHW16_HF_RSI_Lite):
    @property
    def name(self) -> str:
        return "QHW19. 高频布林（轻量近似/止损）"

    @property
    def description(self) -> str:
        return "用 BB(10) 近似短周期上下轨；跌破下轨且放量入场，回到中轨附近退出。"

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        close = _safe_series(out, "Close")
        vol = _safe_series(out, "Volume")
        bb = BollingerBands(close, window=10, window_dev=2)
        out["bb_mid"] = bb.bollinger_mavg()
        out["bb_upper"] = bb.bollinger_hband()
        out["bb_lower"] = bb.bollinger_lband()
        out["vol_ma"] = vol.rolling(max(5, self._p.vol_ma_window // 2)).mean()
        out["volatility"] = _volatility(close, window=10)
        return out

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        close = _safe_series(df, "Close")
        bb_l = pd.to_numeric(df["bb_lower"], errors="coerce")
        bb_m = pd.to_numeric(df["bb_mid"], errors="coerce")
        vol = _safe_series(df, "Volume")
        vol_ma = pd.to_numeric(df["vol_ma"], errors="coerce")
        buy = (close < bb_l) & (vol > vol_ma * 1.1)
        sell = close > bb_m
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


class QHW20_HF_ML_Lite(QlibHighWinBaseStrategy):
    @property
    def name(self) -> str:
        return "QHW20. 高频 ML（轻量因子集成/止损）"

    @property
    def description(self) -> str:
        return "脚本中为 1min ML；此处用多因子打分（动量/均线/波动）近似高频模型决策。"

    def get_start_idx(self) -> int:
        return 60

    def _rule_signals(self, df: pd.DataFrame) -> pd.Series:
        filt = self._passes_liquidity_filters(df)
        close = _safe_series(df, "Close")
        ret5 = close.pct_change(5)
        ret20 = close.pct_change(20)
        ma_s = pd.to_numeric(df["ma_short"], errors="coerce")
        ma_l = pd.to_numeric(df["ma_long"], errors="coerce")
        volat = pd.to_numeric(df["volatility"], errors="coerce")
        # “模型分数”：偏好 ret5/ret20 为正、短均线在上、波动率适中
        score = (
            ret5.rank(pct=True) * 0.35
            + ret20.rank(pct=True) * 0.25
            + (ma_s > ma_l).astype(int).rank(pct=True) * 0.20
            + (-volat).rank(pct=True) * 0.20
        )
        buy = (score > 0.74) & filt
        sell = score < 0.50
        sig = pd.Series(0, index=df.index, dtype=int)
        sig.loc[buy.fillna(False)] = 1
        sig.loc[sell.fillna(False)] = -1
        return sig


def build_qlib_high_win_registry() -> dict[str, type[BaseTradingStrategy]]:
    """导出策略注册表：键为 StrategyFactory 的 strategy_id。"""
    return {
        "QHW01": QHW01_RSI_MeanReversion,
        "QHW02": QHW02_Bollinger_MeanReversion,
        "QHW03": QHW03_MACD_Crossover,
        "QHW04": QHW04_MA_GoldenCross,
        "QHW05": QHW05_Stochastic_Lite,
        "QHW06": QHW06_CCI_Lite,
        "QHW07": QHW07_KDJ_Lite,
        "QHW08": QHW08_WilliamsR_Lite,
        "QHW09": QHW09_RSI_MACD_Resonance,
        "QHW10": QHW10_BB_RSI_Volume,
        "QHW11": QHW11_Alpha158_LiteRank,
        "QHW12": QHW12_DoubleEnsemble_Lite,
        "QHW13": QHW13_XGBoost_Lite,
        "QHW14": QHW14_RandomForest_Lite,
        "QHW15": QHW15_FactorRank_Lite,
        "QHW16": QHW16_HF_RSI_Lite,
        "QHW17": QHW17_HF_MACD_Lite,
        "QHW18": QHW18_HF_Momentum_Lite,
        "QHW19": QHW19_HF_BB_Lite,
        "QHW20": QHW20_HF_ML_Lite,
    }

