#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
技术指标计算
TA-Lib（Technical Analysis Library） 是金融量化中最常用的技术指标库，Python 中通过 talib 包使用。它内置了 150+ 个技术分析函数（指标），分为 7 大类。
下面是 TA-Lib 所有指标的完整分类列表（基于官方文档和最新版本）：
1. Overlap Studies（重叠研究 / 趋势指标）
这些指标会直接叠加在价格图上（如均线、布林带）。

BBANDS — Bollinger Bands（布林带）
DEMA — Double Exponential Moving Average（双指数移动平均）
EMA — Exponential Moving Average（指数移动平均）
HT_TRENDLINE — Hilbert Transform - Instantaneous Trendline
KAMA — Kaufman Adaptive Moving Average（卡夫曼自适应移动平均）
MA — Moving Average（移动平均，可选 SMA/EMA/WMA 等）
MAMA — MESA Adaptive Moving Average
MIDPOINT — MidPoint over period
MIDPRICE — Midpoint Price over period
SAR — Parabolic SAR（抛物线转向）
SAREXT — Parabolic SAR - Extended
SMA — Simple Moving Average（简单移动平均）
T3 — Triple Exponential Moving Average (T3)
TEMA — Triple Exponential Moving Average（三重指数移动平均）
TRIMA — Triangular Moving Average
WMA — Weighted Moving Average（加权移动平均）

2. Momentum Indicators（动量指标）
用于衡量价格变化的速度和强度。

ADX / ADXR — Average Directional Movement Index（平均趋向指数）
APO — Absolute Price Oscillator
AROON / AROONOSC — Aroon / Aroon Oscillator
BOP — Balance of Power
CCI — Commodity Channel Index（顺势指标）
CMO — Chande Momentum Oscillator
DX — Directional Movement Index
MACD / MACDEXT / MACDFIX — MACD（指数平滑异同移动平均线）
MFI — Money Flow Index（资金流量指标）
MINUS_DI / PLUS_DI — Directional Indicators
MINUS_DM / PLUS_DM — Directional Movement
MOM — Momentum（动量）
PPO — Percentage Price Oscillator
ROC / ROCP / ROCR / ROCR100 — Rate of Change
RSI — Relative Strength Index（相对强弱指数）
STOCH / STOCHF / STOCHRSI — Stochastic Oscillator（随机指标）
TRIX — 1-day Rate-Of-Change (ROC) of a Triple Smooth EMA
ULTOSC — Ultimate Oscillator（终极振荡器）
WILLR — Williams %R（威廉指标）

3. Volume Indicators（成交量指标）

AD — Chaikin A/D Line（累积/派发线）
ADOSC — Chaikin A/D Oscillator
OBV — On Balance Volume（能量潮）

4. Volatility Indicators（波动率指标）

ATR — Average True Range（平均真实波动范围）
NATR — Normalized Average True Range
TRANGE — True Range

5. Price Transform（价格变换）

AVGPRICE — Average Price
MEDPRICE — Median Price
TYPPRICE — Typical Price
WCLPRICE — Weighted Close Price

6. Cycle Indicators（周期指标）

HT_DCPERIOD — Hilbert Transform - Dominant Cycle Period
HT_DCPHASE — Hilbert Transform - Dominant Cycle Phase
HT_PHASOR — Hilbert Transform - Phasor Components
HT_SINE — Hilbert Transform - SineWave
HT_TRENDMODE — Hilbert Transform - Trend vs Cycle Mode

7. Pattern Recognition（K线形态识别 / 蜡烛图模式）
TA-Lib 提供了 60+ 个蜡烛图形态识别函数，全部以 CDL 开头，例如：

CDLDOJI — Doji（十字星）
CDLHAMMER — Hammer（锤头线）
CDLENGULFING — Engulfing Pattern（吞没形态）
CDLMORNINGSTAR — Morning Star（晨星）
CDLEVENINGSTAR — Evening Star（暮星）
CDL3BLACKCROWS — Three Black Crows（三只乌鸦）
CDL3WHITESOLDIERS — Three Advancing White Soldiers（三白兵）
...（还有 Shooting Star、Harami、Piercing 等数十种）
"""
import pandas as pd
from typing import Dict, Optional
import akshare as ak
from datetime import datetime, timedelta
from cache_factory import CacheFactory

# 导入 ta 库
from ta.trend import SMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands


class TechIndicatorCalculator:
    """技术指标计算器"""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        """
        初始化
        Args:
            df: 包含OHLCV数据的DataFrame (可选)
        """
        self.df = df
        self.cache = {}
        self.redis_cache = CacheFactory.get_cache()

    def get_stock_history(self, code: str, days: int = 60) -> Optional[pd.DataFrame]:
        """
        获取股票历史K线数据
        
        Args:
            code: 股票代码
            days: 获取天数
            
        Returns:
            包含历史K线数据的DataFrame
        """
        print(f"开始获取 {code} 的 {days} 天历史数据...")
        
        try:
            # 检查缓存
            cache_key = f"{code}_{days}"
            if cache_key in self.cache:
                print(f"从内存缓存获取 {code} 的历史数据")
                return self.cache[cache_key]
            
            # 从Redis获取历史数据
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            print(f"日期范围: {start_date} 到 {end_date}")
            
            history_data = self.redis_cache.get_stock_history(code, start_date, end_date)
            if history_data:
                print(f"从Redis获取 {code} 的历史数据: {len(history_data)} 条")
                # 转换为DataFrame
                df = pd.DataFrame(history_data)
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                df = df.sort_index()
                
                # 缓存结果
                self.cache[cache_key] = df
                print(f"缓存 {code} 的历史数据")
                
                return df
            
            # 如果Redis中没有数据，使用akshare获取
            print(f"Redis中没有数据，调用 akshare 获取 {code} 的历史数据...")
            start_date_str = start_date.replace('-', '')
            end_date_str = end_date.replace('-', '')
            
            df = ak.stock_zh_a_hist(
                symbol=code, 
                period="daily", 
                start_date=start_date_str, 
                end_date=end_date_str, 
                adjust=""
            )
            
            if df is None:
                print(f"akshare 返回 None")
                return None
            
            if df.empty:
                print(f"akshare 返回空数据")
                return None
            
            print(f"akshare 返回数据形状: {df.shape}")
            print(f"akshare 返回列名: {list(df.columns)}")
            
            # 重命名列
            print("重命名列...")
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume',
                '成交额': 'amount',
            })
            
            # 转换日期格式
            print("转换日期格式...")
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 按日期排序
            print("按日期排序...")
            df = df.sort_index()
            
            # 只保留需要的列
            print("只保留需要的列...")
            df = df[['open', 'high', 'low', 'close', 'volume', 'amount']]
            
            print(f"处理后的数据形状: {df.shape}")
            print(f"数据范围: {df.index.min().strftime('%Y-%m-%d')} 到 {df.index.max().strftime('%Y-%m-%d')}")
            
            # 缓存结果
            self.cache[cache_key] = df
            print(f"缓存 {code} 的历史数据")
            
            return df
            
        except Exception as e:
            print(f"获取历史数据失败 {code}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_all_indicators(self) -> Dict:
        """
        获取所有指标
        """
        if self.df is None:
            return {}
        
        print("计算所有技术指标...")
        
        # 使用 ta 库计算技术指标
        indicators = {}
        
        # MACD
        macd_indicator = MACD(close=self.df['close'])
        indicators['macd'] = {
            'macd': macd_indicator.macd(),
            'signal': macd_indicator.macd_signal(),
            'hist': macd_indicator.macd_diff()
        }
        
        # RSI
        rsi_indicator = RSIIndicator(close=self.df['close'], window=14)
        indicators['rsi'] = rsi_indicator.rsi()
        
        # 布林带
        bollinger = BollingerBands(close=self.df['close'], window=20)
        indicators['bollinger'] = {
            'upper': bollinger.bollinger_hband(),
            'middle': bollinger.bollinger_mavg(),
            'lower': bollinger.bollinger_lband()
        }
        
        # 移动平均线
        indicators['ma'] = {
            'ma5': SMAIndicator(close=self.df['close'], window=5).sma_indicator(),
            'ma10': SMAIndicator(close=self.df['close'], window=10).sma_indicator(),
            'ma20': SMAIndicator(close=self.df['close'], window=20).sma_indicator(),
            'ma50': SMAIndicator(close=self.df['close'], window=50).sma_indicator()
        }
        
        return indicators
    
    def calculate_indicators(self, code: str) -> Optional[Dict]:
        """
        计算股票的技术指标
        
        Args:
            code: 股票代码
            
        Returns:
            技术指标数据
        """
        # 获取历史数据
        df = self.get_stock_history(code, days=60)
        if df is None:
            return None
        
        # 计算技术指标
        indicators = {
            'ma5': SMAIndicator(close=df['close'], window=5).sma_indicator().iloc[-1],
            'ma10': SMAIndicator(close=df['close'], window=10).sma_indicator().iloc[-1],
            'ma20': SMAIndicator(close=df['close'], window=20).sma_indicator().iloc[-1],
            'ma50': SMAIndicator(close=df['close'], window=50).sma_indicator().iloc[-1],
            'rsi': RSIIndicator(close=df['close'], window=14).rsi().iloc[-1],
        }
        
        # 计算MACD
        macd_indicator = MACD(close=df['close'])
        indicators['macd'] = {
            'dif': macd_indicator.macd().iloc[-1],
            'dea': macd_indicator.macd_signal().iloc[-1],
            'hist': macd_indicator.macd_diff().iloc[-1]
        }
        
        # 计算布林带
        bollinger = BollingerBands(close=df['close'], window=20)
        indicators['bollinger'] = {
            'upper': bollinger.bollinger_hband().iloc[-1],
            'middle': bollinger.bollinger_mavg().iloc[-1],
            'lower': bollinger.bollinger_lband().iloc[-1]
        }
        
        return indicators
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """
        计算RSI指标
        """
        return RSIIndicator(close=prices, window=period).rsi().iloc[-1]
    
    def calculate_macd(self, prices: pd.Series, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict:
        """
        计算MACD指标
        """
        macd_indicator = MACD(close=prices, window_slow=slow_period, window_fast=fast_period, window_sign=signal_period)
        return {
            'dif': macd_indicator.macd(),
            'dea': macd_indicator.macd_signal(),
            'macd': macd_indicator.macd_diff() * 2  # 保持与原实现一致
        }
    
    def close(self):
        """
        关闭连接（兼容接口）
        """
        pass
