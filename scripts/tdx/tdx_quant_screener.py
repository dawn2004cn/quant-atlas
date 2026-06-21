import os
import logging
import pandas as pd
import numpy as np
import requests
from pytdx.reader import TdxDailyBarReader
from pytdx.hq import TdxHq_API

logger = logging.getLogger(__name__)

# 引入 MyTT 用于写选股公式
from MyTT import *

from typing import List, Dict, Optional, Tuple

from sina_realtime_reader import SinaRealTimeReader
from tdx_config_reader import TdxConfigReader
from tdx_local_data_reader import TdxLocalDataReader
from tdx_realtime_reader import TdxRealTimeReader

from  config import TDX_ROOT_PATH

# ==========================================
# 🔌 1. 核心数据引擎 (维护单次长连接)
# ==========================================
class TdxFastDataClient:
    """通达信极速数据客户端 (维持单例长连接)"""
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.reader = TdxDailyBarReader()
        self.api = TdxHq_API()
        self.is_connected = False

        self.local_reader = TdxLocalDataReader(tdx_path)
        self.realtime_reader = TdxRealTimeReader()
        self.cfg_reader = TdxConfigReader(TDX_ROOT_PATH)
        self.servers = self.cfg_reader.parse_hq_servers()
        # 优选主流行情服务器池
        self.server_pool = [(s['ip'], s['port']) for s in self.servers]

    def connect(self) -> bool:
        """建立全局唯一长连接"""
        if self.is_connected: return True

        for ip, port in self.server_pool:
            try:
                if self.api.connect(ip, port, time_out=3):
                    self.is_connected = True
                    print(f"🔗 成功连接至行情服务器 [{ip}:{port}]")
                    return True
            except Exception as e:
                logger.warning("tdx_quant_screener.connect: %s", e)
                continue

        print("❌ 警告: 无法连接到任何通达信服务器，后续复权数据可能无法获取。")
        return False

    def disconnect(self):
        """安全断开连接"""
        if self.is_connected:
            self.api.disconnect()
            self.is_connected = False
            print("🚫 已安全断开行情服务器连接。")

    def fetch_xdxr_data_fast(self, market: str, code: str) -> pd.DataFrame:
        """通过已有长连接极速拉取除权除息数据"""
        if not self.is_connected:
            return pd.DataFrame()

        market_code = 0 if market == 'sz' else (1 if market == 'sh' else 2)
        try:
            # ⚠️ 核心改变：不在这里 connect/disconnect，直接调用 api
            xdxr_data = self.api.get_xdxr_info(market_code, code)

            if xdxr_data:
                df_xdxr = pd.DataFrame(xdxr_data)
                df_xdxr = df_xdxr[df_xdxr['category'] == 1].copy()
                if not df_xdxr.empty:
                    df_xdxr['date'] = pd.to_datetime(
                        df_xdxr['year'].astype(str) + '-' +
                        df_xdxr['month'].astype(str).str.zfill(2) + '-' +
                        df_xdxr['day'].astype(str).str.zfill(2)
                    )
                    df_xdxr.set_index('date', inplace=True)
                    return df_xdxr
        except Exception as e:
            pass
        return pd.DataFrame()

    def get_qfq_data(self, stock_code: str) -> pd.DataFrame:
        """读取本地二进制数据 + 内存极速前复权"""
        stock_code = stock_code.lower()
        market = stock_code[:2]
        code = stock_code[2:]

        # 1. 读本地文件 (毫秒级)
        file_path = os.path.join(self.tdx_path, 'vipdoc', market, 'lday', f"{stock_code}.day")
        if not os.path.exists(file_path): return pd.DataFrame()
        # ==========================================
        # 🛡️ 修复处：加入强力容错捕获机制，防止单个坏文件搞崩整个程序
        # ==========================================
        try:
            df = self.reader.get_df(file_path)
            # 有时 pytdx 遇到空文件会返回 None 而不是空的 DataFrame
            if df is None or df.empty:
                return pd.DataFrame()
        except Exception as e:
            # 走到这里说明该股票的 .day 文件损坏，打印警告并跳过
            print(f"⚠️ 跳过 {stock_code}: 盘后数据文件已损坏 ({e})")
            return pd.DataFrame()

        df.reset_index(inplace=True)
        df.rename(
            columns={'date': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'vol': 'volume'},
            inplace=True)
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)

        # 2. 拉取除权数据 (依赖外层的长连接，毫秒级)
        df_xdxr = self.fetch_xdxr_data_fast(market, code)

        # 3. 乘性前复权算法
        if not df_xdxr.empty:
            df_xdxr = df_xdxr[['fenhong', 'songzhuangu', 'peigu', 'peigujia']].astype(float)
            df = df.join(df_xdxr, how='left').fillna(0)

            df['pre_close'] = df['close'].shift(1)
            is_xdxr = (df['fenhong'] > 0) | (df['songzhuangu'] > 0) | (df['peigu'] > 0)

            df['theo_price'] = df['pre_close']
            df.loc[is_xdxr, 'theo_price'] = (
                                                    df.loc[is_xdxr, 'pre_close'] - df.loc[is_xdxr, 'fenhong'] / 10 +
                                                    (df.loc[is_xdxr, 'peigu'] / 10) * df.loc[is_xdxr, 'peigujia']
                                            ) / (1 + df.loc[is_xdxr, 'songzhuangu'] / 10 + df.loc[
                is_xdxr, 'peigu'] / 10)

            df['factor'] = 1.0
            valid = is_xdxr & (df['pre_close'] > 0)
            df.loc[valid, 'factor'] = df.loc[valid, 'theo_price'] / df.loc[valid, 'pre_close']

            df['cum_factor'] = df['factor'].cumprod()
            df['qfq_factor'] = df['cum_factor'] / df['cum_factor'].iloc[-1]

            for col in ['open', 'high', 'low', 'close']: df[col] = round(df[col] * df['qfq_factor'], 2)
            df['volume'] = df['volume'] / df['qfq_factor']
            df.drop(columns=['fenhong', 'songzhuangu', 'peigu', 'peigujia', 'pre_close', 'theo_price', 'factor',
                             'cum_factor', 'qfq_factor'], inplace=True)

        return df


# ==========================================
# ⚙️ 2. 选股策略模块 (基于 MyTT 语法)
# ==========================================
class MyTTStrategy:
    """在此处编写你的选股战法"""

    @staticmethod
    def evaluate(df: pd.DataFrame) -> dict:
        """评估股票是否符合买入条件"""
        if len(df) < 60: return {}

        # 将 Pandas 序列转换为 MyTT 需要的 numpy array
        C, O, H, L, V = df['close'].values, df['open'].values, df['high'].values, df['low'].values, df['volume'].values

        # --- 策略：KDJ底部金叉 + MACD零轴上方 ---

        # 1. 算 KDJ
        RSV = (C - LLV(L, 9)) / (HHV(H, 9) - LLV(L, 9)) * 100
        K = SMA(RSV, 3, 1)
        D = SMA(K, 3, 1)
        J = 3 * K - 2 * D

        # 2. 算 MACD
        DIF, DEA, MACD_VAL = MACD(C, 12, 26, 9)

        # 3. 制定买入条件 (要求今天发生)
        KDJ_金叉 = CROSS(K, D)
        KDJ_超卖 = REF(K, 1) < 35  # 昨天K值小于35 (超卖区)
        MACD_强势 = DIF > 0  # MACD必须在水上

        买入信号 = KDJ_金叉 & KDJ_超卖 & MACD_强势

        # 判断今天（最后一天）是否为 True
        if 买入信号[-1]:
            return {"score": 90, "reasons": "KDJ超卖区金叉，且MACD处于零轴上方强势区"}

        return {}


# ==========================================
# 🗄️ 3. 数据层：历史读取 + 实时获取 + 动态拼接
# ==========================================
class DataFeedManager:
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.local_reader = TdxLocalDataReader()
        self.realtime_reader = TdxRealTimeReader()
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
            logger.warning("tdx_quant_screener.get_xdxr: %s", e)
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
            logger.warning("tdx_quant_screener.get_realtime: %s", e)
            return {}

# ==========================================
# 🚀 3. 极速扫描引擎 (统筹全局)
# ==========================================
class FastScreenerEngine:
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.client = TdxFastDataClient(tdx_path)
        self.local_reader = TdxLocalDataReader(tdx_path)
        self.real_reader = SinaRealTimeReader()

    def get_custom_block(self, block_name="ZXG.blk") -> list:
        """
        读取通达信自定义板块/自选股
        :param block_name: 默认为 'ZXG.blk' (自选股)。
                           如果你在通达信建了叫"新能源"的板块，这里传入 "新能源.blk"
        """
        blk_path = os.path.join(self.tdx_path, "T0002", "blocknew", block_name)
        stocks = []

        if not os.path.exists(blk_path):
            print(f"❌ 找不到板块文件: {blk_path}")
            return stocks

        with open(blk_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if len(line) == 7:  # 标准格式: 1位市场码 + 6位股票代码
                    market_flag = line[0]
                    code = line[1:]

                    if market_flag == '0':
                        market = 'sz'
                    elif market_flag == '1':
                        market = 'sh'
                    elif market_flag == '2':
                        market = 'bj'
                    else:
                        continue

                    stocks.append(f"{market}{code}")

        return stocks

    def run_screener(self, block_name="ZXG.blk"):
        """执行极速扫描流水线"""
        my_stocks = self.get_custom_block(block_name)
        if not my_stocks:
            print("股票池为空或文件不存在！")
            return

        print(f"🚀 开始扫描股票池: {block_name} (共 {len(my_stocks)} 只)")
        results = []

        # 🌟🌟 核心优化：只在这里建立一次网络连接 🌟🌟
        is_net_ready = self.client.connect()

        try:
            # 高速循环处理每一只股票
            for idx, ticker in enumerate(my_stocks):
                if idx % 50 == 0 and idx > 0:
                    print(f"  ... 已扫描 {idx} 只股票 ...{ticker}")

                # 1. 拿数据 (内部复用了长连接拉取除权数据)
                #df = self.client.get_qfq_data(ticker)
                df = self.local_reader.get_stock_data(ticker,adjust=True)

                # 2. 跑策略
                res = MyTTStrategy.evaluate(df)

                if res:
                    results.append({
                        "代码": ticker,
                        "最新价": df['close'].iloc[-1],
                        "打分": res.get("score", 0),
                        "入选逻辑": res.get("reasons", "")
                    })
        finally:
            # 🌟🌟 无论程序正常跑完还是报错中断，必须在此安全断开连接 🌟🌟
            self.client.disconnect()

        # 打印报表
        report_df = pd.DataFrame(results)
        print("\n" + "=" * 70)
        print("🎯 极 速 扫 描 结 果")
        print("=" * 70)

        if report_df.empty:
            print("当前市场环境下，股票池中没有任何股票触发买入信号。")
        else:
            report_df = report_df.sort_values(by="打分", ascending=False)
            print(report_df.to_string(index=False))


# ==========================================
# 🏁 4. 运行入口
# ==========================================
if __name__ == "__main__":
    #TDX_ROOT_PATH = r"E:\\tdx\\通达信金融终端(开心果交易版)V2024.02"  # ⚠️ 修改你的通达信路径

    engine = FastScreenerEngine(TDX_ROOT_PATH)

    # 扫描默认的 "自选股" (ZXG.blk)
    # 如果你想扫描整个 A 股市场，可以读取 "A股.blk"（取决于你在通达信里保存的名字）
    engine.run_screener("ZXG.blk")