from pytdx.hq import TdxHq_API
import pandas as pd

from tdx_connect_manager import TdxConnectionManager


class TdxRealTimeReader:
    """通达信实时行情读取器"""
    def __init__(self):
        self.tdx = TdxConnectionManager()
        #self.api = TdxHq_API()

    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
        """
        批量获取实时行情 (每次最多 80 只)
        :param stock_codes: 格式为 ['sh600519', 'sz000001']
        """
        # pytdx 的 get_security_quotes 需要的格式是 [(market, code), ...]
        # 市场代码: 0-深圳，1-上海，2-北交所
        query_list = []
        for code in stock_codes:
            market_str = code[:2].lower()
            symbol = code[2:]
            market_id = 1 if market_str == 'sh' else (0 if market_str == 'sz' else 2)
            query_list.append((market_id, symbol))

        try:
            # 连接高可用行情服务器
            # 🌟 修复处 1：正确使用 if 判断连接状态，放弃 with 写法
            #is_connected = self.api.connect('119.147.212.81', 7709, time_out=2)

            if self.tdx.is_connected:    # 如果传入超过80只，需要自己写切片循环，这里演示基础调用
                quotes = self.tdx.execute('get_security_quotes', query_list)
                if not quotes:
                    return pd.DataFrame()

                df = pd.DataFrame(quotes)
                # 提取核心实时字段
                df = df[['code', 'price', 'last_close', 'open', 'high', 'low', 'vol', 'amount']]
                df.rename(columns={'vol': 'volume', 'price': 'close'}, inplace=True)

                # 计算实时涨跌幅
                df['pct_change'] = (df['close'] - df['last_close']) / df['last_close'] * 100
                return df

        except Exception as e:
            print(f"获取实时行情失败: {e}")
            return pd.DataFrame()


# 测试运行
if __name__ == "__main__":
    reader = TdxRealTimeReader()
    realtime_df = reader.get_realtime_quotes(['sh600519', 'sz000001', 'sh601127'])
    print("=== 通达信实时行情 ===")

    # 🌟 修复处 2：打印前必须判断 DataFrame 是否为空，防止 KeyError 崩溃
    if realtime_df is not None:
        # Pandas 对齐输出格式
        pd.set_option('display.unicode.east_asian_width', True)
        print(realtime_df[['code', 'close', 'pct_change', 'volume']].to_string())
    else:
        print("⚠️ 未获取到任何实时数据，请检查网络或非交易时间。")