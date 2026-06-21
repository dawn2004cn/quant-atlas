import os
import sys
import time
import datetime
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import requests
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple
from pytdx.reader import TdxDailyBarReader
from pytdx.hq import TdxHq_API

from app.core.logger import get_logger

logger = get_logger(__name__)

# 导入 TA 库
from ta.trend import SMAIndicator, MACD
from ta.momentum import StochasticOscillator
from ta.volatility import BollingerBands

import warnings

warnings.filterwarnings('ignore')

# ==========================================
# ⚙️ 1. 全局配置
# ==========================================
TDX_ROOT_PATH = r"E:\\tdx\\通达信金融终端(开心果交易版)V2024.02"  # ⚠️ 修改为你电脑上的通达信安装目录


# ==========================================
# 📊 2. 指标计算工厂 (纯静态方法)
# ==========================================
class AdvancedIndicators:
    @staticmethod
    def calc_ma(df: pd.DataFrame, period: int) -> pd.Series:
        return SMAIndicator(close=df['close'], window=period).sma_indicator()

    @staticmethod
    def calc_macd(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        macd = MACD(close=df['close'])
        return macd.macd(), macd.macd_signal(), macd.macd_diff() * 2

    @staticmethod
    def calc_kdj(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        stoch = StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=9, smooth_window=3)
        stoch_k, stoch_d = stoch.stoch(), stoch.stoch_signal()
        k, d = stoch_d, stoch_k
        return k, d, 3 * k - 2 * d

    @staticmethod
    def calc_bb(df: pd.DataFrame, window: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        bb = BollingerBands(close=df['close'], window=window, window_dev=2.0)
        return bb.bollinger_hband(), bb.bollinger_mavg(), bb.bollinger_lband()

    @staticmethod
    def calc_vol_ratio(df: pd.DataFrame, window: int = 5) -> pd.Series:
        past_ma = df['volume'].shift(1).rolling(window=window).mean()
        return df['volume'] / past_ma.replace(0, np.nan)


# ==========================================
# 🗄️ 3. 数据层：历史读取 + 实时获取 + 动态拼接
# ==========================================
class DataFeedManager:
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.reader = TdxDailyBarReader()
        self.hq_api = TdxHq_API()

    def _get_qfq_factor(self, market: str, code: str) -> pd.DataFrame:
        """获取前复权因子数据"""
        market_code = 0 if market == 'sz' else 1
        try:
            with self.hq_api.connect('119.147.212.81', 7709, time_out=2):
                xdxr_data = self.hq_api.get_xdxr_info(market_code, code)
                if xdxr_data:
                    df_xdxr = pd.DataFrame(xdxr_data)
                    df_xdxr = df_xdxr[df_xdxr['category'] == 1].copy()
                    if not df_xdxr.empty:
                        df_xdxr['date'] = pd.to_datetime(
                            df_xdxr['year'].astype(str) + '-' + df_xdxr['month'].astype(str).str.zfill(2) + '-' +
                            df_xdxr['day'].astype(str).str.zfill(2))
                        df_xdxr.set_index('date', inplace=True)
                        return df_xdxr
        except Exception as e:
            logger.warning("quant_screener.get_xdxr: %s", e)
        return pd.DataFrame()

    def get_historical_data(self, stock_code: str) -> pd.DataFrame:
        """读取通达信本地日线并前复权"""
        market = stock_code[:2].lower()
        code = stock_code[2:]
        file_path = os.path.join(self.tdx_path, 'vipdoc', market, 'lday', f"{stock_code}.day")

        if not os.path.exists(file_path): return pd.DataFrame()

        df = self.reader.get_df(file_path)
        if df.empty: return df

        df.reset_index(inplace=True)
        df.rename(
            columns={'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'vol': 'volume',
                     'amount': 'amount'}, inplace=True)
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)

        # 执行复权 (简化版，仅处理分红送转缺口保障趋势连续)
        df_xdxr = self._get_qfq_factor(market, code)
        if not df_xdxr.empty:
            df_xdxr = df_xdxr[['fenhong', 'songzhuangu']].astype(float)
            df = df.join(df_xdxr, how='left').fillna(0)
            df['pre_close'] = df['close'].shift(1)
            is_xdxr = (df['fenhong'] > 0) | (df['songzhuangu'] > 0)

            df['theo_price'] = df['pre_close']
            df.loc[is_xdxr, 'theo_price'] = (df.loc[is_xdxr, 'pre_close'] - df.loc[is_xdxr, 'fenhong'] / 10) / (
                        1 + df.loc[is_xdxr, 'songzhuangu'] / 10)

            df['factor'] = 1.0
            valid = is_xdxr & (df['pre_close'] > 0)
            df.loc[valid, 'factor'] = df.loc[valid, 'theo_price'] / df.loc[valid, 'pre_close']

            df['cum_factor'] = df['factor'].cumprod()
            df['qfq_factor'] = df['cum_factor'] / df['cum_factor'].iloc[-1]

            for col in ['open', 'high', 'low', 'close']: df[col] = round(df[col] * df['qfq_factor'], 2)
            df['volume'] = df['volume'] / df['qfq_factor']
            df.drop(columns=['fenhong', 'songzhuangu', 'pre_close', 'theo_price', 'factor', 'cum_factor', 'qfq_factor'],
                    inplace=True)

        return df

    def get_realtime_data(self, stock_codes: List[str]) -> Dict[str, dict]:
        """批量获取新浪实时行情"""
        if not stock_codes: return {}
        url = f"http://hq.sinajs.cn/list={','.join(stock_codes)}"
        headers = {'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'}

        try:
            res = requests.get(url, headers=headers, timeout=5)
            lines = res.text.strip().split('\n')
            rt_data = {}
            for line in lines:
                if len(line) < 20: continue
                code = line.split('=')[0].split('_')[-1]
                data = line.split('"')[1].split(',')
                rt_data[code] = {
                    'name': data[0],
                    'open': float(data[1]),
                    'pre_close': float(data[2]),
                    'close': float(data[3]),
                    'high': float(data[4]),
                    'low': float(data[5]),
                    'volume': float(data[8]) / 100,  # 新浪返回股数，通达信通常用手(100股)
                    'amount': float(data[9]),
                    'time': data[31]
                }
            return rt_data
        except Exception as e:
            logger.warning("quant_screener.get_realtime: %s", e)
            return {}


# ==========================================
# 🧠 4. 选股模型库 (Strategy Pattern)
# ==========================================
class BaseSelectionModel(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> Optional[Dict]: pass


class BreakoutModel(BaseSelectionModel):
    @property
    def name(self) -> str:
        return "🚀 布林带放量突破"

    def evaluate(self, df: pd.DataFrame) -> Optional[Dict]:
        if len(df) < 25: return None
        up, mid, low = AdvancedIndicators.calc_bb(df)
        vol_ratio = AdvancedIndicators.calc_vol_ratio(df).iloc[-1]

        c_today = df['close'].iloc[-1]
        c_yest = df['close'].iloc[-2]

        # 今日收盘站上上轨，昨日还在上轨之下，且量比大于 2.0
        if c_today > up.iloc[-1] and c_yest <= up.iloc[-2] and vol_ratio > 2.0:
            return {"score": 90, "reasons": f"放量突破布林上轨 (量比 {vol_ratio:.1f})"}
        return None


class KDJBottomCrossModel(BaseSelectionModel):
    @property
    def name(self) -> str:
        return "⚡ KDJ 底部黄金坑"

    def evaluate(self, df: pd.DataFrame) -> Optional[Dict]:
        if len(df) < 20: return None
        k, d, j = AdvancedIndicators.calc_kdj(df)

        # 金叉且发生在 30 以下的超卖区
        if k.iloc[-1] > d.iloc[-1] and k.iloc[-2] <= d.iloc[-2] and k.iloc[-2] < 30:
            if j.iloc[-2] < 0 and j.iloc[-1] > 0:
                return {"score": 95, "reasons": "KDJ超卖区金叉，且J线触底强力反弹穿越0轴！"}
            return {"score": 80, "reasons": "KDJ超卖区金叉。"}
        return None


# ==========================================
# 🚂 5. 核心引擎 (历史与实时组装器)
# ==========================================
class IntradayScreenerEngine:
    def __init__(self, tdx_path: str):
        self.data_feed = DataFeedManager(tdx_path)
        self.models: List[BaseSelectionModel] = []

    def register_model(self, model: BaseSelectionModel):
        self.models.append(model)

    def _predict_full_day_volume(self, current_vol: float, current_time_str: str) -> float:
        """🔥 核心黑科技：盘中成交量动态折算算法"""
        try:
            now = datetime.datetime.strptime(current_time_str, "%H:%M:%S").time()
            # 交易时间段：9:30-11:30, 13:00-15:00 (共 240 分钟)
            trade_minutes = 0
            if now < datetime.time(9, 30): return current_vol
            if now <= datetime.time(11, 30):
                trade_minutes = (now.hour - 9) * 60 + now.minute - 30
            elif now < datetime.time(13, 0):
                trade_minutes = 120
            elif now <= datetime.time(15, 0):
                trade_minutes = 120 + (now.hour - 13) * 60 + now.minute
            else:
                trade_minutes = 240

            trade_minutes = max(1, trade_minutes)
            return current_vol * (240 / trade_minutes)  # 按比例放大至全天
        except Exception as e:
            logger.warning("quant_screener.estimate_volume: %s", e)
            return current_vol

    def run(self, stock_list: List[str]):
        logger.info("启动引擎，正在拉取实时行情与历史数据 (共 %s 只)", len(stock_list))
        results = []
        today = pd.Timestamp.today().normalize()

        # 1. 批量获取实时数据 (新浪接口支持一次查几百只)
        rt_quotes = self.data_feed.get_realtime_data(stock_list)

        for code in stock_list:
            # 2. 获取本地历史前复权日线
            df_hist = self.data_feed.get_historical_data(code)
            if df_hist.empty: continue

            # 3. 实时数据拼接处理
            rt = rt_quotes.get(code)
            if rt and rt['open'] > 0:  # 停牌股票 open 为 0
                last_hist_date = df_hist.index[-1]

                # 如果历史数据没更新到今天，进行动态拼接！
                if last_hist_date < today:
                    predicted_vol = self._predict_full_day_volume(rt['volume'], rt['time'])

                    today_row = pd.DataFrame([{
                        'open': rt['open'],
                        'high': rt['high'],
                        'low': rt['low'],
                        'close': rt['close'],
                        'volume': predicted_vol,  # 使用预测全天量！
                        'amount': rt['amount']
                    }], index=[today])

                    df_combined = pd.concat([df_hist, today_row])
                else:
                    df_combined = df_hist
            else:
                df_combined = df_hist

            # 4. 送入选股模型进行评估
            for model in self.models:
                res = model.evaluate(df_combined)
                if res:
                    results.append({
                        "代码": code,
                        "名称": rt['name'] if rt else "未知",
                        "最新价": df_combined['close'].iloc[-1],
                        "战法模型": model.name,
                        "打分": res['score'],
                        "触发逻辑": res['reasons']
                    })

        return pd.DataFrame(results)


# ==========================================
# 🏁 6. 主入口运行
# ==========================================
if __name__ == "__main__":
    # 初始化引擎
    engine = IntradayScreenerEngine(TDX_ROOT_PATH)

    # 注册模型
    engine.register_model(BreakoutModel())
    engine.register_model(KDJBottomCrossModel())

    # 设定自选股池 (格式：sh+代码 或 sz+代码)
    my_pool = [
        'sh600519', 'sz000001', 'sh601127', 'sz002594', 'sz000858',
        'sh600036', 'sz002475', 'sz300750', 'sh601012', 'sz002739'
    ]

    # 执行盘中扫描
    report = engine.run(my_pool)

    logger.info("=" * 80)
    logger.info("盘中动态实时选股报告")
    logger.info("=" * 80)

    if report.empty:
        logger.info("当前盘口下，自选股池中没有股票触发核心买点")
    else:
        report = report.sort_values(by="打分", ascending=False)
        pd.set_option('display.unicode.east_asian_width', True)
        logger.info("\n%s", report.to_string(index=False))