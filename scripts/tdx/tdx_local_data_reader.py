import os
import sys
import traceback

from app.infrastructure.external.tdx_selector import TDX_SERVERS

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
from pytdx.reader import TdxDailyBarReader
from pytdx.hq import TdxHq_API

from tdx_config_reader import TdxConfigReader
from tdx_connect_manager import TdxConnectionManager

try:
    from app.config import TDX_ROOT_PATH
except ImportError:
    TDX_ROOT_PATH = r"E:\tdx\通达信金融终端(开心果交易版)V2024.02"


class TdxLocalDataReader:
    """通达信本地日线数据读取器 (支持精准前复权)"""
    def __init__(self, tdx_path: str):
         # 你的通达信路径
        if tdx_path is not None:
            self.tdx_path = tdx_path
        else:
            self.tdx_path = TDX_ROOT_PATH
        self.is_connected = False
        self.reader = TdxDailyBarReader()
        self.tdx = TdxConnectionManager()
        # 优选主流行情服务器池
        #self.server_pools = [(s['ip'], s['port']) for s in self.servers]
        # 收集的高质量通达信行情服务器列表 (含电信、联通、移动多线)


    def _get_market_folder(self, market: str) -> str:
        market = market.lower()
        if market in ['sh', 'sz', 'bj']:
            return os.path.join(self.tdx_path, 'vipdoc', market, 'lday')
        raise ValueError("市场参数错误，只能是 'sh', 'sz', 'bj'")

    def _get_tdx_market_code(self, market: str) -> int:
        """pytdx 在线 API 市场代码映射"""
        if market == 'sz': return 0
        if market == 'sh': return 1
        if market == 'bj': return 2
        return 0

    def fetch_xdxr_data(self, market: str, code: str) -> pd.DataFrame:
        """多服务器轮询拉取除权数据 (已修复 bool 上下文报错)"""
        market_code = 0 if market == 'sz' else (1 if market == 'sh' else 2)
        if not self.is_connected:
            return pd.DataFrame()
        for ip, port in self.server_pool:
            try:
                # 正确的用法：if 判断连接是否成功
                is_connected = self.ap.connect(ip, port, time_out=2)

                if self.tdx.is_connected:
                    # 连接成功，拉取除权除息数据
                    #xdxr_data = self.api.get_xdxr_info(market_code, code)
                    xdxr_data = self.tdx.execute('get_xdxr_info', market_code, code)
                    #self.api.disconnect()  # 数据拉完后立即手动断开连接

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
                        else:
                            # 股票存在，但历史上没有分红送转记录
                            return pd.DataFrame()
                    else:
                        # 接口返回空
                        return pd.DataFrame()
                else:
                    # 当前 IP 连接失败，循环尝试下一个 IP
                    continue

            except Exception as e:
                # 发生异常时确保连接被安全断开
                continue

                # print(f"⚠️ 警告: 尝试了所有服务器，均无法获取 {market}{code} 的除权数据，将返回未复权数据。")
        return pd.DataFrame()
    def fetch_xdxr_data(self, market: str, code: str) -> pd.DataFrame:
        """
        通过 pytdx 接口在线获取股票的除权除息(XDXR)数据
        """
        if not self.is_connected:
            return pd.DataFrame()
        market_code = self._get_tdx_market_code(market)

        try:
            # 连接通达信公共行情服务器 (这里使用默认的高可用IP)
            #with self.hq_api.connect('119.147.212.81', 7709):
            if self.tdx.is_connected:
                #xdxr_data = self.api.get_xdxr_info(market_code, code)
                xdxr_data = self.tdx.execute('get_xdxr_info', market_code, code)
            if not xdxr_data:
                return pd.DataFrame()

            df_xdxr = pd.DataFrame(xdxr_data)

            # category == 1 代表除权除息日
            df_xdxr = df_xdxr[df_xdxr['category'] == 1].copy()
            if df_xdxr.empty:
                return pd.DataFrame()

            # 拼接出日期字段并设为索引
            df_xdxr['date'] = pd.to_datetime(
                df_xdxr['year'].astype(str) + '-' +
                df_xdxr['month'].astype(str).str.zfill(2) + '-' +
                df_xdxr['day'].astype(str).str.zfill(2)
            )
            df_xdxr.set_index('date', inplace=True)
            return df_xdxr

        except Exception as e:
            print(f"获取 {market}{code} 除权数据失败: {e}")
            return pd.DataFrame()

    def qfq_adjust(self, df: pd.DataFrame, df_xdxr: pd.DataFrame) -> pd.DataFrame:
        """
        执行向量化前复权计算 (乘性复权)
        """
        # 如果没有除权数据，直接返回原数据
        if df_xdxr.empty:
            return df

        # 提取相关字段，通达信返回的数值是"每10股"的数值
        df_xdxr = df_xdxr[['fenhong', 'songzhuangu', 'peigu', 'peigujia']].astype(float)

        # 将除权数据合并到日线数据中 (按日期对齐)
        df = df.join(df_xdxr, how='left')

        # 填充没有除权除息日子的 NaN 为 0
        df[['fenhong', 'songzhuangu', 'peigu', 'peigujia']] = df[
            ['fenhong', 'songzhuangu', 'peigu', 'peigujia']].fillna(0)

        # 算出前一日收盘价 (用于计算理论除权价)
        df['pre_close'] = df['close'].shift(1)

        # ----------------------------------------------------
        # 核心复权算法：计算单日除权因子
        # ----------------------------------------------------
        # 当天有除权除息操作时，计算除权缺口比例
        is_xdxr = (df['fenhong'] > 0) | (df['songzhuangu'] > 0) | (df['peigu'] > 0)

        # 公式：理论除权价 = (前收盘 - 分红/10 + 配股/10 * 配股价) / (1 + 送转/10 + 配股/10)
        df['theoretical_price'] = df['pre_close']
        df.loc[is_xdxr, 'theoretical_price'] = (
                                                       df.loc[is_xdxr, 'pre_close']
                                                       - df.loc[is_xdxr, 'fenhong'] / 10
                                                       + (df.loc[is_xdxr, 'peigu'] / 10) * df.loc[is_xdxr, 'peigujia']
                                               ) / (1 + df.loc[is_xdxr, 'songzhuangu'] / 10 + df.loc[
            is_xdxr, 'peigu'] / 10)

        # 当日变动因子 = 理论除权价 / 前收盘价
        # 如果前收盘价为0或NaN，因子设为1
        df['factor'] = 1.0
        valid_idx = is_xdxr & (df['pre_close'] > 0)
        df.loc[valid_idx, 'factor'] = df.loc[valid_idx, 'theoretical_price'] / df.loc[valid_idx, 'pre_close']

        # 计算累计复权因子
        df['cum_factor'] = df['factor'].cumprod()

        # 计算前复权因子 (让最新一天的累计因子归 1.0，越往前的历史K线，复权因子越小)
        latest_cum_factor = df['cum_factor'].iloc[-1]
        df['qfq_factor'] = df['cum_factor'] / latest_cum_factor

        # ----------------------------------------------------
        # 执行调价
        # ----------------------------------------------------
        for col in ['open', 'high', 'low', 'close']:
            df[col] = round(df[col] * df['qfq_factor'], 2)

        # 成交量与价格成反比，需要除以因子
        df['volume'] = df['volume'] / df['qfq_factor']

        # 清理过程计算列
        df.drop(columns=[
            'fenhong', 'songzhuangu', 'peigu', 'peigujia',
            'pre_close', 'theoretical_price', 'factor', 'cum_factor', 'qfq_factor'
        ], inplace=True)

        return df

    def get_stock_data(self, stock_code: str, adjust: bool = True) -> pd.DataFrame:
        """
        读取单只股票数据，并支持复权
        :param stock_code: 代码，如 'sz000001'
        :param adjust: 是否开启前复权 (默认 True)
        """
        stock_code = stock_code.lower()
        market = stock_code[:2]
        code = stock_code[2:]

        # 1. 读取本地二进制 `.day` 文件
        folder_path = self._get_market_folder(market)
        file_path = os.path.join(folder_path, f"{stock_code}.day")

        if not os.path.exists(file_path):
            return pd.DataFrame()

        df = self.reader.get_df(file_path)
        if df.empty:
            return df

        # 数据清洗
        df.reset_index(inplace=True)
        df.rename(columns={
            'date': 'date', 'open': 'open', 'high': 'high',
            'low': 'low', 'close': 'close', 'vol': 'volume', 'amount': 'amount'
        }, inplace=True)
        df.set_index('date', inplace=True)
        df.index = pd.to_datetime(df.index)

        # 2. 检查是否需要复权
        if adjust:
            # 联网拉取除权数据表
            df_xdxr = self.fetch_xdxr_data(market, code)
            # 实施向量化复权
            df = self.qfq_adjust(df, df_xdxr)

        return df


# ==========================================
# 🚀 运行验证：不复权 vs 前复权
# ==========================================
if __name__ == "__main__":
    TDX_ROOT_PATH = r"E:\\tdx\\通达信金融终端(开心果交易版)V2024.02"  # 你的通达信路径

    tdx_reader = TdxLocalDataReader(TDX_ROOT_PATH)

    # 贵州茅台 (历史上分红极多)
    ticker = "sh600519"

    print(f"正在读取 {ticker} 原始数据(不复权)...")
    df_raw = tdx_reader.get_stock_data(ticker, adjust=False)

    print(df_raw.tail(5))
    print(f"正在读取 {ticker} 前复权数据...")
    df_qfq = tdx_reader.get_stock_data(ticker, adjust=True)

    print(df_qfq.tail(5))
    if not df_raw.empty and not df_qfq.empty:
        # 比较 2001-08-27 茅台上市首日的价格
        try:
            date_check = '2015-08-27'
            raw_close = df_raw.loc[date_check, 'close']
            qfq_close = df_qfq.loc[date_check, 'close']

            print("\n📊 {date_check}【复权威力对比】(贵州茅台上市首日收盘价):")
            print(f"👉 原始价格 (通达信原文件): {raw_close} 元")
            print(f"👉 前复权价格 (用于量化指标): {qfq_close:.2f} 元")
            print("💡 如果不用前复权，你的系统会认为茅台这二十年从35元跌到了1元以下，导致所有指标死叉失灵！")
        except KeyError:
            print("未找到对应的历史数据日期。")
