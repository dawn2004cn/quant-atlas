import json
import re
from abc import ABC, abstractmethod

import datetime
import requests
import yfinance as yf
from mlflow.tracing.utils import timeout
from pytdx.hq import TdxHq_API
import pandas as pd
from redis.cache import CacheFactory
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator, MACD


class BaseRealTimeReader(ABC):
    @property
    @abstractmethod
    def name(self) -> str: pass

    @abstractmethod
    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame: pass


class TdxRealTimeReader:
    """通达信实时行情读取器"""
    def __init__(self):
        #self.tdx = TdxConnectionManager()  # 使用连接管理器来获取高可用连接
        self.tdx = None

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
                #quotes = self.api.get_security_quotes(query_list)

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
class TencentRealTimeReader:
    """
        腾讯财经实时行情接口 (极速版)
        接口地址:
        从腾讯接口获取股票数据

        Args:
            param stock_codes: ['sh600519', 'sz000001']
            # Multiple stocks
            curl -s "http://qt.gtimg.cn/q=sh600519,sh000001,sz399001"
        Returns:
            tuple: (DataFrame, 错误信息)
            v_sh600519="1~贵州茅台~600519~1440.00~1460.00~1460.05~17268~7673~9588~1439.60~1~1439.59~1~1439.57~1~1439.40~1~1439.32~1~1440.00~2~1440.29~3~1440.43~1~1440.48~1~1440.60~1~~20260407135341~-20.00~-1.37~1470.00~1439.01~1440.00/17268/2516608938~17268~251661~0.14~20.03~~1470.00~1439.01~2.12~18032.69~18032.69~7.94~1606.00~1314.00~0.74~-3~1457.39~20.93~20.91~~~0.52~251660.8938~0.0000~0~ ~GP-A~4.56~1.41~3.59~35.02~30.58~1593.44~1322.01~2.27~3.08~4.56~1252270215~1252270215~-23.08~3.44~1252270215~~~-0.58~0.00~~CNY~0~___D__F__N~1439.26~51~";
            v_sh000001="1~上证指数~000001~3888.43~3880.10~3884.15~377400539~0~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~20260407135342~8.33~0.21~3902.61~3875.68~3888.43/377400539/582363069699~377400539~58236307~0.79~16.93~~3902.61~3875.68~0.69~599052.56~638951.83~0.00~-1~-1~0.93~0~3890.51~~~~~~58236306.9699~0.0000~0~ ~ZS~-2.03~-0.89~~~~4197.23~3070.08~1.97~-5.08~-2.03~4798335202075~~9.95~11.18~4798335202075~~~25.57~0.15~~CNY~0~~0.00~0~";
            v_sz399001="51~深证成指~399001~13409.69~13352.90~13392.94~435667695~0~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~0.00~0~~20260407135342~56.79~0.43~13476.08~13305.51~13409.69/435667695/711105711900~435667695~71110571~1.80~50.46~~13476.08~13305.51~1.28~374077.75~435126.35~0.00~-1~-1~0.94~0~13405.42~~~~~~71110571.1900~0.0000~0~ ~ZS~-0.85~-2.31~~~~14536.08~9119.60~0.48~-4.68~-0.85~2417119461409~~13.74~26.65~2417119461409~~~43.20~0.20~~CNY~0~~0.00~0~";

        """

    def __init__(self):
        # 伪装请求头，防止被墙
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
        """
        批量获取实时行情
        :param stock_codes: 格式为 ['sh600519', 'sh000001', 'sz399001']
        :return: 包含清洗后行情的 pandas DataFrame
        """
        if not stock_codes:
            return pd.DataFrame()

        # 腾讯接口单次建议不超过 60 只股票，拼接 URL
        url = f"http://qt.gtimg.cn/q={','.join(stock_codes)}"

        try:
            response = requests.get(url, headers=self.headers, timeout=3)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ 获取腾讯实时行情失败: {e}")
            return pd.DataFrame()

        # 按行分割返回的字符串
        lines = response.text.strip().split('\n')
        data_list = []

        for line in lines:
            if len(line) < 20:
                continue

            try:
                # 解析原始字符串: v_sh600519="1~贵州茅台~600519~1440.00~..."
                # 提取引号中的内容
                raw_data_str = line.split('="')[1].replace('";', '')
                items = raw_data_str.split('~')

                # 如果切割后的字段太少，说明返回的是错误代码，跳过
                if len(items) < 40:
                    continue

                # 辅助函数：安全转换为 float，处理空字符串
                def safe_float(val):
                    try:
                        return float(val) if val else 0.0
                    except ValueError:
                        return 0.0

                # ==========================================
                # 🎯 腾讯 API 核心字段索引映射 (极为珍贵)
                # ==========================================
                row = {
                    'code': items[2],  # 股票代码
                    'name': items[1],  # 股票名称
                    'datetime': items[30],  # 时间 (YYYYMMDDHHMMSS)
                    'open': safe_float(items[5]),  # 今日开盘价
                    'pre_close': safe_float(items[4]),  # 昨日收盘价
                    'close': safe_float(items[3]),  # 最新价/当前价
                    'high': safe_float(items[33]),  # 最高价
                    'low': safe_float(items[34]),  # 最低价
                    'volume': safe_float(items[6]),  # 成交量 (单位：手)
                    'amount': safe_float(items[37]),  # 成交额 (单位：万元)
                    'pct_change': safe_float(items[32]),  # 涨跌幅 (%)
                    'price_chg': safe_float(items[31]),  # 涨跌额
                    'turnover_rate': safe_float(items[38]),  # 换手率 (%)
                    'pe': safe_float(items[39]),  # 市盈率 (TTM)
                    'pb': safe_float(items[46]),  # 市净率
                    'amplitude': safe_float(items[43]),  # 振幅 (%)
                    'total_mv': safe_float(items[45]),  # 总市值 (亿元)
                    'limit_up': safe_float(items[47]),  # 涨停价
                    'limit_down': safe_float(items[48])  # 跌停价
                }
                data_list.append(row)

            except IndexError as e:
                print(f"⚠️ 解析某行数据时出错: {e} | 数据片段: {line[:30]}")
                continue

        df = pd.DataFrame(data_list)

        # 将 datetime 字符串 (如 20260407135341) 转换为 pandas 的时间格式
        if not df.empty and 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], format='%Y%m%d%H%M%S', errors='coerce')

        return df


class yFinanceRealTimeReader:
    """
    A robust interface for fetching real-time stock quotes using yfinance.
    """
    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
        """
        Fetches core market data for a list of stock tickers.

        Args:
            stock_codes (list): List of ticker symbols (e.g., ['AAPL', '600519.SS'])

        Returns:
            pd.DataFrame: A formatted table containing prices and daily metrics.
        """
        if not stock_codes:
            return pd.DataFrame()

        # Initialize the Tickers object to handle batch requests
        tickers_obj = yf.Tickers(" ".join(stock_codes))
        data_list = []

        for code in stock_codes:
            try:
                ticker = tickers_obj.tickers[code]
                # .fast_info provides price, volume, and high/low without the overhead of .info
                info = ticker.fast_info

                # Calculate change manually to ensure accuracy
                current_price = info.last_price
                prev_close = info.previous_close
                change_pct = ((current_price / prev_close) - 1) * 100 if prev_close else 0

                data_list.append({
                    "Ticker": code,
                    "Price": round(current_price, 2),
                    "Change %": f"{change_pct:.2f}%",
                    "Open": round(info.open, 2),
                    "High": round(info.day_high, 2),
                    "Low": round(info.day_low, 2),
                    "Volume": int(info.last_volume),
                    "UpdateTime": datetime.datetime.now().strftime("%H:%M:%S")
                })
            except Exception as e:
                print(f"Warning: Could not fetch {code} -> {e}")
                continue

        return pd.DataFrame(data_list)

    def get_market_overview(self, tickers: list) -> list:
        """获取全景图（批量获取最新行情）"""
        results = []
        # 使用批量下载提升速度
        data = yf.download(tickers, period="1d", group_by="ticker", progress=False)

        for ticker in tickers:
            try:
                # 处理 yfinance 多重索引返回
                if len(tickers) == 1:
                    df = data
                else:
                    df = data[ticker]

                if not df.empty:
                    open_price = float(df['Open'].iloc[-1])
                    close_price = float(df['Close'].iloc[-1])
                    pct_chg = (close_price - open_price) / open_price * 100

                    results.append({
                        "ticker": ticker,
                        "price": round(close_price, 2),
                        "pct_chg": round(pct_chg, 2),
                        "volume": int(df['Volume'].iloc[-1])
                    })
            except Exception as e:
                print(f"解析 {ticker} 失败: {e}")
        return results

    def get_stock_history_with_ta(self, ticker: str, period: str = "6mo") -> pd.DataFrame:
        """获取个股历史数据并计算 TA 指标"""
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty:
            return df

        # 统一列名处理
        df.reset_index(inplace=True)
        df['Date'] = df['Date'].dt.strftime('%Y-%m-%d')

        # --- 计算技术指标 (TA库) ---
        # 1. 均线
        df['MA20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
        df['MA60'] = SMAIndicator(close=df['Close'], window=60).sma_indicator()

        # 2. MACD
        macd = MACD(close=df['Close'])
        df['MACD_DIF'] = macd.macd()
        df['MACD_DEA'] = macd.macd_signal()
        df['MACD_HIST'] = macd.macd_diff() * 2

        # 3. RSI
        df['RSI'] = RSIIndicator(close=df['Close'], window=14).rsi()

        # 填充空值为 0 (方便传给前端 JSON)
        df.fillna(0, inplace=True)
        return df

    def get_stock_news(self, ticker: str) -> list:
        """获取个股最新新闻"""
        stock = yf.Ticker(ticker)
        try:
            news_list = stock.news
            formatted_news = []
            for item in news_list[:5]:  # 取最近5条
                formatted_news.append({
                    "title": item.get('title', ''),
                    "publisher": item.get('publisher', ''),
                    "link": item.get('link', ''),
                    # yfinance 新闻的时间戳转换
                    "time": pd.to_datetime(item.get('providerPublishTime', 0), unit='s').strftime('%Y-%m-%d %H:%M')
                })
            return formatted_news
        except Exception:
            return []

#
# class SohuRealTimeReader:
#     """
#     通过搜狐财经接口获取股票数据。
#     注意：此接口通常返回最近的交易日数据（包含开高低收、涨跌幅等）。
#     """
#
#     def __init__(self):
#         self.base_url = "https://q.stock.sohu.com/hisHq"
#         self.headers = {
#             "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
#         }
#
#     def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
#         """
#         获取股票数据
#         :param stock_codes: 股票代码列表，搜狐格式通常为 cn_600519, cn_000001
#         """
#         all_data = []
#
#         # 搜狐接口支持批量，但建议循环处理以保证容错
#         for code in stock_codes:
#             # 搜狐代码规则：A股需要加上 'cn_' 前缀
#             formatted_code = f"cn_{code.split('.')[0]}" if "cn_" not in code else code
#
#             params = {
#                 "code": formatted_code,
#                 "stat": "1"  # 状态参数
#             }
#
#             try:
#                 response = requests.get(self.base_url, params=params, headers=self.headers)
#                 data = response.json()
#
#                 # 搜狐返回的是一个列表，[0] 是状态，hq 是行情主体
#                 if isinstance(data, list) and len(data) > 0:
#                     stock_info = data[0]
#                     if 'hq' in stock_info:
#                         # 获取最新的那一条行情 (通常是列表的最后一行或第一行，取决于接口返回)
#                         latest_day = stock_info['hq'][0]
#
#                         row = {
#                             "Code": code,
#                             "Date": latest_day[0],
#                             "Open": latest_day[1],
#                             "Close": latest_day[2],
#                             "Change": latest_day[3],
#                             "Change %": latest_day[4],
#                             "Low": latest_day[5],
#                             "High": latest_day[6],
#                             "Volume": latest_day[7],
#                             "Turnover": latest_day[8]
#                         }
#                         all_data.append(row)
#             except Exception as e:
#                 print(f"Error fetching {code} from Sohu: {e}")
#                 continue
#
#         return pd.DataFrame(all_data)



class SohuRealTimeReader:

    def __init__(self):
        self.url = "https://hqm.stock.sohu.com/getqjson"
        self.headers = {
            "Referer": "https://q.stock.sohu.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_realtime_quotes(self, stock_codes: list) -> pd.DataFrame:
        """
        获取实时报价
        :param stock_codes: 代码列表，如 ['cn_920509', 'cn_688661']
            使用搜狐实时 JSONP 接口 (hqm.stock.sohu.com) 获取行情
         fortune_hq_cn(
         {"cn_000001":["cn_000001","平安银行","11.03","-0.81%","-0.09","607955","4512","67132","0.31%","0.66","11.14","10.97","5.02","11.12","11.12","/cn/000001/index.shtml","2140.44","2026-04-07 15:00:57","/t/cn/001/000001.html"],"cn_600519":["cn_600519","贵州茅台","1440.02","-1.37%","-19.98","24152","395","350747","0.19%","0.75","1470.00","1435.05","20.03","1460.00","1460.05","/cn/600519/index.shtml","18032.94","2026-04-07 15:00:56","/t/cn/519/600519.html"]})
         code,name,close,change_pre,change,总量（手）,未知，成交量，换手，量比，high，low，市盈率，open，昨收，url，市值(亿),datetime,url
         0     1    2     3          4       5       6    7    8   9    10   11   12    13    13   14   15      16        17
        """
        if not stock_codes:
            return pd.DataFrame()

        # 构造请求参数
        params = {
            "code": ",".join(stock_codes),
            "cb": "fortune_hq_cn",
            "_": int(datetime.datetime.now().timestamp())  # 时间戳防止缓存
        }
        url = f"https://hqm.stock.sohu.com/getqjson?code={",".join(stock_codes)}&cb=fortune_hq_cn&_={int(datetime.datetime.now().timestamp())}"
        print(url)
        print(params)
        try:
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            response.encoding = 'gb2312'  #
            print(response.text)
            # 使用正则提取 JSON 内容: fortune_hq_cn([...]); -> [...]
            # 1. 提取 JSON 内容
            pattern = r'fortune_hq_cn\((\{.*\})\)'
            match = re.search(pattern, response.text, re.S)

            if match:
                data = match.group(1)
                print(data)
            #match = re.search(r'fortune_hq_cn\((.*)\)', response.text)
            if not match:
                return pd.DataFrame()
            if not match:
                print("Failed to parse JSONP response")
                return pd.DataFrame()

            raw_data = json.loads(match.group(1))

            # 解析字段映射 (搜狐该接口返回的是一个嵌套列表)
            # 索引参考：0:代码, 1:名称, 2:最新价, 3:涨跌额, 4:涨跌幅, 7:开盘, 8:昨收, 9:最高, 10:最低...
            formatted_results = []
            for key in raw_data:
                print(key)
                #if len(item) < 15: continue  # 跳过异常数据
                item = raw_data[key]

                formatted_results.append({
                    "Symbol": item[0],
                    "Name": item[1],
                    "Price": float(item[2]),
                    "Change": (item[4]),
                    "Change%": item[3],
                    "Open": float(item[12]),
                    "PrevClose": (item[13]),
                    "High": float(item[10]),
                    "Low": float(item[11]),
                    "Volume": item[5],
                    "Amount": float(item[7])/10000,
                    "Time": item[16]
                })

            return pd.DataFrame(formatted_results)

        except Exception as e:
            print(f"Request error: {e}")
            return pd.DataFrame()

    def get_realtime_market_movements(self):
        """后台获取并缓存市场异动数据"""
        try:
            print("🔄 后台更新市场异动数据...")

            # 调用搜狐API获取市场异动数据
            url = 'https://hqm.stock.sohu.com/gethqtop.up?cb=fortune_hq'
            response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            print(f"✅ API 响应状态: {response.status_code}")

            # 直接获取原始字节数据，然后尝试不同的编码
            response_content = response.content
            print(f"📄 响应字节长度: {len(response_content)} 字节")

            # 尝试不同的编码
            response_text = None
            encodings = ['gbk', 'utf-8', 'gb2312']

            for encoding in encodings:
                try:
                    response_text = response_content.decode(encoding)
                    print(f"✅ 编码 {encoding} 解码成功")
                    print(f"📝 响应开头: {response_text[:100]}...")
                    # 检查是否包含 JSONP 包装
                    if 'fortune_hq(' in response_text:
                        print(f"✅ 找到 JSONP 包装")
                        break
                except Exception as e:
                    print(f"❌ 编码 {encoding} 解码失败: {e}")
                    continue

            if not response_text:
                print("❌ 无法解析响应")
                return

            print(f"📄 响应长度: {len(response_text)} 字符")

            # 移除JSONP包装
            if 'fortune_hq(' in response_text:
                # 找到 JSONP 包装的开始位置
                start_idx = response_text.find('fortune_hq(')
                if start_idx != -1:
                    # 找到 JSONP 包装的结束位置
                    end_idx = response_text.rfind(');')
                    if end_idx != -1:
                        json_str = response_text[start_idx + 11:end_idx]
                        print(f"📄 JSON 长度: {len(json_str)} 字符")

                        # 尝试直接解析
                        try:
                            print("🔄 尝试直接解析 JSON...")
                            data = json.loads(json_str)
                            print("✅ 直接解析成功!")
                        except json.JSONDecodeError as e:
                            print(f"❌ 直接解析失败: {e}")
                            # 尝试处理编码问题
                            try:
                                print("🔄 尝试使用 gbk 编码...")
                                # 先将字符串编码为 bytes，再用 gbk 解码
                                json_str_bytes = json_str.encode('latin1')
                                json_str_gbk = json_str_bytes.decode('gbk')
                                data = json.loads(json_str_gbk)
                                print("✅ GBK 编码解析成功!")
                            except Exception as e2:
                                print(f"❌ 所有编码尝试失败: {e2}")
                                return
                    else:
                        print("❌ 无法找到 JSONP 包装的结束位置")
                        return
                else:
                    print("❌ 无法找到 JSONP 包装的开始位置")
                    return
            else:
                print("❌ API 响应格式错误")
                return

            # 处理异动数据
            movements = []
            dxjl_data = data.get('dxjl', [])
            print(f"📈 dxjl 类型: {type(dxjl_data)}")
            print(f"📈 dxjl 长度: {len(dxjl_data)}")

            if isinstance(dxjl_data, list):
                for item in dxjl_data:
                    if isinstance(item, dict):
                        # 打印 item 结构，查看是否包含涨幅信息
                        print(f"📋 item 结构: {list(item.keys())}")
                        print(f"📋 item 数据: {item}")

                        # 提取股票代码（去除cn_前缀）
                        stock_code = item.get('code', '').replace('cn_', '')

                        # 转换时间格式
                        time_str = item.get('time', '')

                        # 从本地缓存中获取股票的涨幅信息
                        change = ''
                        try:
                            cache = CacheFactory.get_cache()
                            stock_data = cache.get_stock(stock_code)
                            if stock_data and stock_data.get('change_pct') is not None:
                                change_pct = stock_data['change_pct']
                                change = f"{change_pct:+.2f}%"
                        except Exception as e:
                            print(f"❌ 获取股票涨幅失败: {e}")
                        print(f"📈 {item.get('name', '')} 涨幅: {change}")

                        movement = {
                            'code': stock_code,
                            'name': item.get('name', ''),
                            'type': item.get('type', ''),
                            'time': time_str,
                            'change': change
                        }
                        movements.append(movement)
                        print(f"✅ 添加异动: {movement['name']} - {movement['type']} - {change}")

            print(f"📋 最终异动数据数量: {len(movements)}")

            # 只有当有数据时才保存到缓存
            if movements:
                # 保存到缓存
                print("💾 保存到缓存...")
                cache = CacheFactory.get_cache()
                cache.save_market_movements(movements)
                print("✅ 保存成功")

            print(f"✅ 市场异动数据已更新: {len(movements)} 条")
        except Exception as e:
            print(f"❌ 后台更新市场异动数据失败: {e}")
# 测试运行
if __name__ == "__main__":
    # 填入你要查询的股票 (包含大盘指数)
    stocks = ['sh600519', 'sh000001', 'sz399001']
    #
    # reader = TdxRealTimeReader()
    # tdxrealtime_df = reader.get_realtime_quotes(stocks)
    # print("=== 通达信实时行情 ===")
    # # 🌟 修复处 2：打印前必须判断 DataFrame 是否为空，防止 KeyError 崩溃
    # if tdxrealtime_df is not None:
    #     # Pandas 对齐输出格式
    #     pd.set_option('display.unicode.east_asian_width', True)
    #     print(tdxrealtime_df[['code', 'close', 'pct_change', 'volume']].to_string())
    # else:
    #     print("⚠️ 未获取到任何实时数据，请检查网络或非交易时间。")

    # sina_reader = SinaRealTimeReader()
    # sina_df = sina_reader.get_realtime_quotes(stocks)
    #
    # if sina_df is not None:
    #     # Pandas 对齐输出格式
    #     pd.set_option('display.unicode.east_asian_width', True)
    #     print(sina_df[['code', 'close',  'volume']].to_string())
    # else:
    #     print("⚠️ 未获取到任何实时数据，请检查网络或非交易时间。")
    # treader = TencentRealTimeReader()
    #
    # # 填入你要查询的股票 (包含大盘指数)
    # stocks = ['sh600519', 'sh000001', 'sz399001']
    # trealtime_df = treader.get_realtime_quotes(stocks)
    #
    # print("正在向腾讯财经拉取实时数据...")
    # if trealtime_df is not None:
    #     # Pandas 对齐输出格式
    #     pd.set_option('display.unicode.east_asian_width', True)
    #     print(trealtime_df[['code', 'close', 'pct_change', 'volume']].to_string())
    # else:
    #     print("⚠️ 未获取到任何实时数据，请检查网络或非交易时间。")

    reader = yFinanceRealTimeReader()

    # Portfolio mix: Tech, Crypto (via Yahoo), and China A-Shares
    my_stocks = ['AAPL', 'BTC-USD', '600519.SS']

    df = reader.get_realtime_quotes(my_stocks)
    print("--- Real-Time Market Feed ---")
    print(df.to_string(index=False))


    sohu_reader = SohuRealTimeReader()
    # 搜狐接口通常直接输入数字代码，我们在类中处理了 cn_ 前缀
    stocks = ['cn_600519', 'cn_000001']

    df = sohu_reader.get_realtime_quotes(stocks)
    print(df)