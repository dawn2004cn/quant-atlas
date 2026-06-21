import requests
import pandas as pd


class SinaRealTimeReader:
    """新浪财经实时行情获取器"""

    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
        """
        :param stock_codes: ['sh600519', 'sz000001']
        """
        # 拼接 URL，格式: http://hq.sinajs.cn/list=sh600519,sz000001
        url = f"http://hq.sinajs.cn/list={','.join(stock_codes)}"

        # ⚠️ 突破新浪防盗链的核心机制
        headers = {
            'Referer': 'https://finance.sina.com.cn',
            'User-Agent': 'Mozilla/5.0'
        }

        try:
            res = requests.get(url, headers=headers, timeout=3)
            lines = res.text.strip().split('\n')

            results = []
            for line in lines:
                if len(line) < 20: continue
                # 解析新浪返回的字符串: var hq_str_sh600519="贵州茅台,27.55,27.25,26.91,..."
                code = line.split('=')[0].split('_')[-1]
                data_str = line.split('"')[1]
                data = data_str.split(',')

                results.append({
                    'code': code,
                    'name': data[0],
                    'open': float(data[1]),
                    'last_close': float(data[2]),
                    'close': float(data[3]),  # 当前价
                    'high': float(data[4]),
                    'low': float(data[5]),
                    'volume': float(data[8]),
                    'amount': float(data[9]),
                    'time': data[31]
                })
            return pd.DataFrame(results)
        except Exception as e:
            print(f"获取新浪行情失败: {e}")
            return pd.DataFrame()


# 测试运行
if __name__ == "__main__":
    reader = SinaRealTimeReader()
    df = reader.get_realtime_quotes(['sh600519', 'sz000001'])
    print("\n=== 新浪财经实时行情 ===")
    print(df[['code', 'name', 'close', 'high', 'low', 'time']].to_string())