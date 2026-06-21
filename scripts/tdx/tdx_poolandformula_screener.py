import os
import pandas as pd
import numpy as np

# 导入我们之前写的 TdxLocalDataReader (假设你已经保存好了)
# 从上面的代码复制 TdxLocalDataReader 类到这里，或者 import 进来
from tdx_local_data_reader import TdxLocalDataReader

# 🌟 核心：导入通达信公式复刻库
from MyTT import *


class TdxPoolAndFormulaScreener:
    def __init__(self, tdx_path: str):
        self.tdx_path = tdx_path
        self.reader = TdxLocalDataReader(tdx_path)

    def get_custom_block_stocks(self, block_name="ZXG.blk") -> list:
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

    def run_tdx_formula(self, df: pd.DataFrame) -> bool:
        """
        核心：在这里用 Python 语法 1:1 运行通达信公式
        """
        if len(df) < 65: return False

        # 将 Pandas 的列转为 numpy 数组 (MyTT 需要的数据格式)
        C = df['close'].values
        O = df['open'].values
        H = df['high'].values
        L = df['low'].values
        V = df['volume'].values

        # ==========================================
        # ⬇️ 几乎完美复刻的通达信公式区 ⬇️
        # ==========================================

        # MA20:=MA(C,20);
        MA20 = MA(C, 20)

        # MA60:=MA(C,60);
        MA60 = MA(C, 60)

        # DIF:=EMA(C,12)-EMA(C,26); DEA:=EMA(DIF,9); MACD:=(DIF-DEA)*2;
        DIF, DEA, MACD = MACD(C, 12, 26, 9)

        # 金叉:=CROSS(DIF,DEA);
        金叉 = CROSS(DIF, DEA)

        # 多头:=C>MA20 AND C>MA60;
        # 注意: numpy 数组的逻辑与必须用 &
        多头 = (C > MA20) & (C > MA60)

        # 买入: 多头 AND 金叉;
        买入 = 多头 & 金叉

        # ==========================================
        # ⬆️ 通达信公式区结束 ⬆️
        # ==========================================

        # 买入信号是一个 True/False 的数组，我们只看今天(最后一天)是否触发 [-1]
        return 买入[-1]

    def scan_pool(self, block_name="ZXG.blk"):
        """扫描股票池"""
        print(f"📂 正在读取通达信板块: {block_name} ...")
        my_stocks = self.get_custom_block_stocks(block_name)

        print(f"✅ 找到 {len(my_stocks)} 只股票，开始执行通达信选股公式...\n")

        selected_stocks = []
        for ticker in my_stocks:
            try:
                # 获取复权历史数据
                df = self.reader.get_stock_data(ticker, adjust=True)
                if df.empty: continue

                # 运行公式
                if self.run_tdx_formula(df):
                    selected_stocks.append({
                        "代码": ticker,
                        "最新价": df['close'].iloc[-1],
                        "状态": "🔥 触发【多头MACD金叉】买入信号!"
                    })
            except Exception as e:
                pass

        # 打印输出
        result_df = pd.DataFrame(selected_stocks)
        return result_df


# ==========================================
# 🚀 运行
# ==========================================
if __name__ == "__main__":
    # 配置通达信目录
    TDX_PATH = r"E:\\tdx\\通达信金融终端(开心果交易版)V2024.02"

    screener = TdxPoolAndFormulaScreener(TDX_PATH)

    # 扫描默认的 "自选股"
    report = screener.scan_pool("ZXG.blk")

    # 如果你在通达信里新建了一个叫 "华为概念" 的板块，就可以这样扫：
    # report = screener.scan_pool("华为概念.blk")

    print("=" * 60)
    print("🎯 通 达 信 公 式 扫 描 报 告")
    print("=" * 60)

    if report.empty:
        print("💡 自选股池中目前没有股票触发该通达信公式。")
    else:
        print(report.to_string(index=False))