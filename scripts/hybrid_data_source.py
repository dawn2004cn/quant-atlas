#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混合数据源管理器
整合 Tushare Pro + 新浪财经 + akshare
优先级: Tushare > 新浪 > akshare
"""

import akshare as ak
import tushare as ts
import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd


class HybridDataSource:
    """混合数据源管理器"""
    
    def __init__(self, tushare_token: Optional[str] = None):
        """
        初始化数据源
        
        Args:
            tushare_token: Tushare Pro token (可选)
                          注册地址: https://tushare.pro/register
        """
        self.tushare_token = tushare_token
        self.tushare_available = False
        
        # akshare全市场数据缓存
        self.akshare_market_cache = None
        self.akshare_cache_time = None
        self.akshare_cache_expiry = 300  # 缓存5分钟
        
        # 尝试初始化Tushare
        if tushare_token:
            try:
                ts.set_token(tushare_token)
                self.pro = ts.pro_api()
                # 测试连接
                self.pro.trade_cal(exchange='SSE', start_date='20260101', end_date='20260101')
                self.tushare_available = True
                print("Tushare Pro 已连接")
            except Exception as e:
                print(f"Tushare Pro 连接失败: {e}")
                print("   将使用 新浪财经 + akshare 作为备用")
        else:
            print("未配置 Tushare token，使用 新浪财经 + akshare")
    
    def get_realtime_price(self, code: str) -> Optional[Dict]:
        """
        获取实时价格（智能策略：优先使用新浪，失败后再用akshare）
        
        Args:
            code: 股票代码 (如 '600900')
            
        Returns:
            {'code': str, 'name': str, 'price': float, 'change_pct': float, ...}
        """
        # 首先尝试新浪财经（无论是否交易时间）
        result = self._get_sina_realtime(code)
        if result:
            return result
        
        # 新浪失败：使用akshare
        result = self._get_akshare_realtime(code)
        return result
    
    def get_realtime_batch(self, codes: List[str]) -> List[Dict]:
        """
        批量获取实时价格（交易时间尝试新浪批量，盘后用akshare逐个）
        
        Args:
            codes: 股票代码列表
            
        Returns:
            [{'code': str, 'name': str, 'price': float, ...}, ...]
        """
        from datetime import datetime, time as dt_time
        
        # 判断是否交易时间
        now = datetime.now()
        current_time = now.time()
        weekday = now.weekday()
        
        is_trading = False
        if weekday < 5:
            morning_start = dt_time(9, 15)
            morning_end = dt_time(11, 30)
            afternoon_start = dt_time(13, 0)
            afternoon_end = dt_time(15, 0)
            is_trading = (morning_start <= current_time <= morning_end) or \
                        (afternoon_start <= current_time <= afternoon_end)
        
        if is_trading:
            # 交易时间：尝试新浪批量（但可能超时）
            result = self._get_sina_batch(codes)
            if result and len(result) > 0:
                return result
        
        # 盘后或新浪失败：逐个查询
        results = []
        for code in codes:
            data = self.get_realtime_price(code)
            if data:
                results.append(data)
        
        return results
    
    def get_history_data(self, code: str, days: int = 120) -> Optional[pd.DataFrame]:
        """
        获取历史数据（优先级：Tushare > Yahoo财经 > 新浪财经 > 东方财富 > akshare > 本地缓存）
        
        Args:
            code: 股票代码
            days: 天数
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume, amount
        """
        # 方案1: Tushare（推荐，数据质量高）
        if self.tushare_available:
            result = self._get_tushare_history(code, days)
            if result is not None and not result.empty:
                return result
        
        # 方案2: Yahoo财经（免费，稳定）
        result = self._get_yahoo_history(code, days)
        if result is not None and not result.empty:
            return result
        
        # 方案3: 新浪财经（免费，稳定）
        result = self._get_sina_history(code, days)
        if result is not None and not result.empty:
            return result
        
        # 方案4: 东方财富（免费，备用）
        result = self._get_eastmoney_history(code, days)
        if result is not None and not result.empty:
            return result
        
        # 方案5: akshare（备用）
        result = self._get_akshare_history(code, days)
        if result is not None and not result.empty:
            return result
        
        # 方案6: 尝试从本地缓存获取
        result = self._get_cached_history(code, days)
        return result
    
    def _get_sina_realtime(self, code: str) -> Optional[Dict]:
        """新浪财经实时行情（使用新浪行情接口）"""
        try:
            # 转换股票代码格式
            if code.startswith('6'):
                symbol = f'sh{code}'
            else:
                symbol = f'sz{code}'
            
            # 使用新浪行情接口
            url = f'http://qt.gtimg.cn/q={symbol}'
            response = requests.get(url, timeout=3)
            response.encoding = 'gbk'
            
            if response.status_code != 200:
                return None
            
            # 解析数据
            data = response.text
            if f'v_{symbol}=' in data:
                # 提取数据部分
                data_part = data.split('=')[1].strip('"\n')
                items = data_part.split('~')
                
                if len(items) >= 32:
                    return {
                        'code': code,
                        'name': items[1],
                        'price': float(items[3]),
                        'change_pct': float(items[31]),
                        'volume': int(items[8]),
                        'amount': float(items[9]) * 10000,
                        'turnover': float(items[37]) if len(items) > 37 and items[37] else 0,  # 换手率
                        'open': float(items[4]),
                        'high': float(items[6]),
                        'low': float(items[5]),
                        'prev_close': float(items[2]),
                        'source': 'sina'
                    }
        except Exception as e:
            print(f"新浪财经获取失败 {code}: {e}")
            return None
    
    def _get_sina_batch(self, codes: List[str]) -> Optional[List[Dict]]:
        """新浪财经批量查询（使用新浪行情接口）"""
        try:
            # 转换为新浪格式
            symbols = []
            for code in codes:
                if code.startswith('6'):
                    symbols.append(f'sh{code}')
                else:
                    symbols.append(f'sz{code}')
            
            # 新浪限制：一次最多50只
            if len(symbols) > 50:
                symbols = symbols[:50]
            
            symbol_str = ','.join(symbols)
            url = f'http://qt.gtimg.cn/q={symbol_str}'
            response = requests.get(url, timeout=5)
            response.encoding = 'gbk'
            
            if response.status_code != 200:
                return None
            
            # 解析批量数据
            results = []
            lines = response.text.strip().split('\n')
            
            for i, line in enumerate(lines):
                if 'v_' not in line:
                    continue
                
                code = codes[i] if i < len(codes) else None
                if not code:
                    continue
                
                data_part = line.split('=')[1].strip('"\n')
                items = data_part.split('~')
                
                if len(items) < 32:
                    continue
                
                results.append({
                    'code': code,
                    'name': items[1],
                    'price': float(items[3]),
                    'change_pct': float(items[31]),
                    'volume': int(items[8]),
                    'amount': float(items[9]) * 10000,
                    'turnover': float(items[37]) if len(items) > 37 and items[37] else 0,  # 换手率
                    'source': 'sina_batch'
                })
            
            return results if results else None
        except Exception as e:
            print(f"新浪批量查询失败: {e}")
            return None
    
    def _get_tushare_realtime(self, code: str) -> Optional[Dict]:
        """Tushare实时行情"""
        try:
            # 转换为Tushare格式
            if code.startswith('6'):
                ts_code = f'{code}.SH'
            else:
                ts_code = f'{code}.SZ'
            
            # 获取今日行情
            today = datetime.now().strftime('%Y%m%d')
            df = self.pro.daily(ts_code=ts_code, trade_date=today)
            
            if df.empty:
                return None
            
            row = df.iloc[0]
            change_pct = row['pct_chg']
            
            return {
                'code': code,
                'name': '',  # Tushare不返回名称，需要额外查询
                'price': row['close'],
                'change_pct': change_pct,
                'volume': row['vol'] * 100,  # 手转股
                'amount': row['amount'] * 1000,  # 千元转元
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'prev_close': row['pre_close'],
                'source': 'tushare'
            }
        except Exception as e:
            print(f"Tushare获取失败 {code}: {e}")
            return None
    
    def _get_akshare_realtime(self, code: str) -> Optional[Dict]:
        """akshare实时行情"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 检查缓存是否有效
                current_time = time.time()
                if (self.akshare_market_cache is None or 
                    self.akshare_cache_time is None or 
                    current_time - self.akshare_cache_time > self.akshare_cache_expiry):
                    # 缓存过期，重新获取全市场数据
                    print("ℹ️ 刷新akshare全市场数据缓存...")
                    self.akshare_market_cache = ak.stock_zh_a_spot_em()
                    self.akshare_cache_time = current_time
                
                df = self.akshare_market_cache
                
                if df is None or df.empty:
                    return None
                
                stock = df[df['代码'] == code]
                
                if stock.empty:
                    return None
                
                row = stock.iloc[0]
                
                return {
                    'code': code,
                    'name': row['名称'],
                    'price': row['最新价'],
                    'change_pct': row['涨跌幅'],
                    'volume': row['成交量'],
                    'amount': row['成交额'],
                    'turnover': row.get('换手率', 0),
                    'source': 'akshare'
                }
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"第 {attempt + 1} 次尝试获取akshare实时数据失败: {e}")
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"akshare获取失败 {code}: {e}")
                    return None
    
    def _get_tushare_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """Tushare历史数据"""
        try:
            # 转换为Tushare格式
            if code.startswith('6'):
                ts_code = f'{code}.SH'
            else:
                ts_code = f'{code}.SZ'
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
            
            df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
            
            if df.empty:
                return None
            
            # 转换为标准格式
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume',
            })
            
            # 成交量单位转换（手 -> 股）
            df['volume'] = df['volume'] * 100
            df['amount'] = df['amount'] * 1000
            
            # 按日期排序
            df = df.sort_values('date')
            
            return df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']].tail(days)
        except Exception as e:
            print(f"Tushare历史数据获取失败 {code}: {e}")
            return None
    
    def _get_yahoo_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """Yahoo财经历史数据（使用 test_yahoo_finance.py 的方式）"""
        try:
            import yfinance as yf
            import pandas as pd
            import os
            from datetime import datetime, timedelta
            
            # 设置 yfinance 缓存目录到可写位置
            cache_dir = os.path.join(os.path.dirname(__file__), 'yfinance_cache')
            os.makedirs(cache_dir, exist_ok=True)
            
            # 设置环境变量，让 yfinance 使用可写的缓存目录
            os.environ['HOME'] = os.path.dirname(__file__)
            os.environ['TMPDIR'] = cache_dir
            os.environ['TEMP'] = cache_dir
            
            # 转换股票代码为Yahoo格式
            if code.startswith('6'):
                yahoo_code = f"{code}.SS"  # 上海证券交易所
            else:
                yahoo_code = f"{code}.SZ"  # 深圳证券交易所
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            # 使用 yfinance 获取数据（按照 test_yahoo_finance.py 的方式）
            df = yf.download(
                tickers=yahoo_code,
                start=start_date,
                end=end_date,
                interval="1d",           # "1d","1wk","1mo"
                auto_adjust=True,
                threads=True
            )
            
            if df is None or df.empty:
                return None
            
            # 处理数据
            df = df.reset_index()
            df = df.rename(columns={
                'Date': 'date',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # 计算成交额
            df['amount'] = df['close'] * df['volume']
            
            # 确保日期格式正确
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            
            return df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']].tail(days)
        except Exception as e:
            print(f"Yahoo财经历史数据获取失败 {code}: {e}")
            return None

    def _get_akshare_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """akshare历史数据"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                # 计算日期范围
                end_date = datetime.now().strftime('%Y%m%d')
                start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')
                
                df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date, end_date=end_date, adjust="")
                
                if df is None or df.empty:
                    return None
                
                # 重命名列
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount',
                })
                
                return df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']].tail(days)
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"第 {attempt + 1} 次尝试获取akshare历史数据失败: {e}")
                    print(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    print(f"akshare历史数据获取失败 {code}: {e}")
                    return None

    def _get_sina_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """新浪财经历史数据"""
        try:
            # 使用 data_fetchers.py 中的搜狐接口
            from data_fetchers import fetch_from_sohu
            from datetime import datetime, timedelta
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            # 从搜狐接口获取数据
            df, error = fetch_from_sohu(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 确保有 amount 列
                if 'amount' not in df.columns:
                    df['amount'] = df['close'] * df['volume']
                
                # 重置索引，确保 date 是列
                if df.index.name == 'date':
                    df = df.reset_index()
                
                # 确保列名正确
                df = df.rename(columns={
                    'date': 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'amount': 'amount'
                })
                
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                if all(col in df.columns for col in required_columns):
                    return df[required_columns].tail(days)
            
            return None
        except Exception as e:
            print(f"新浪财经历史数据获取失败 {code}: {e}")
            return None

    def _get_eastmoney_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """东方财富历史数据"""
        try:
            # 使用 data_fetchers.py 中的腾讯接口
            from data_fetchers import fetch_from_tencent
            from datetime import datetime, timedelta
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            # 从腾讯接口获取数据
            df, error = fetch_from_tencent(code, start_date, end_date)
            
            if df is not None and not df.empty:
                # 确保有 amount 列
                if 'amount' not in df.columns:
                    df['amount'] = df['close'] * df['volume']
                
                # 重置索引，确保 date 是列
                if df.index.name == 'date':
                    df = df.reset_index()
                
                # 确保列名正确
                df = df.rename(columns={
                    'date': 'date',
                    'open': 'open',
                    'high': 'high',
                    'low': 'low',
                    'close': 'close',
                    'volume': 'volume',
                    'amount': 'amount'
                })
                
                required_columns = ['date', 'open', 'high', 'low', 'close', 'volume', 'amount']
                if all(col in df.columns for col in required_columns):
                    return df[required_columns].tail(days)
            
            return None
        except Exception as e:
            print(f"东方财富历史数据获取失败 {code}: {e}")
            return None

    def _get_cached_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """从本地缓存获取历史数据"""
        try:
            from stock_cache_db import StockCache
            import pandas as pd
            from datetime import datetime, timedelta
            
            # 从数据库缓存获取历史数据
            cache = StockCache()
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y-%m-%d')
            
            # 从缓存获取历史数据
            history_data = cache.get_stock_history(code, start_date, end_date)
            cache.close()
            
            if history_data and len(history_data) >= days:
                print(f"从数据库缓存获取到 {len(history_data)} 天历史数据")
                # 转换为 DataFrame
                df = pd.DataFrame(history_data)
                return df.tail(days)
            
            # 检查是否存在本地文件缓存
            import os
            import json
            
            cache_dir = 'data_cache'
            os.makedirs(cache_dir, exist_ok=True)
            cache_file = os.path.join(cache_dir, f'{code}_history.json')
            
            if os.path.exists(cache_file):
                # 读取缓存文件
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 转换为 DataFrame
                df = pd.DataFrame(data)
                
                # 检查数据是否足够
                if len(df) >= days:
                    print(f"从本地文件缓存获取到 {len(df)} 天历史数据")
                    return df.tail(days)
            
            # 不生成模拟数据，直接返回 None
            print(f"本地缓存不足，返回空数据")
            return None
        except Exception as e:
            print(f"本地缓存历史数据获取失败 {code}: {e}")
            return None
    
    def _generate_mock_history(self, code: str, days: int) -> Optional[pd.DataFrame]:
        """生成模拟历史数据"""
        try:
            import pandas as pd
            import numpy as np
            from datetime import datetime, timedelta
            
            # 生成日期范围
            end_date = datetime.now()
            dates = [end_date - timedelta(days=i) for i in range(days)][::-1]
            
            # 生成模拟数据
            base_price = 10.0
            prices = []
            current_price = base_price
            
            for _ in range(days):
                # 随机波动
                change = np.random.normal(0, 0.02)  # 2% 的日波动率
                current_price *= (1 + change)
                prices.append(current_price)
            
            # 生成其他数据
            opens = [p * (1 + np.random.normal(0, 0.01)) for p in prices]
            highs = [max(o, p * (1 + np.random.uniform(0, 0.03))) for o, p in zip(opens, prices)]
            lows = [min(o, p * (1 - np.random.uniform(0, 0.03))) for o, p in zip(opens, prices)]
            volumes = [int(np.random.normal(1000000, 500000)) for _ in range(days)]
            amounts = [p * v for p, v in zip(prices, volumes)]
            
            # 创建 DataFrame
            df = pd.DataFrame({
                'date': [d.strftime('%Y-%m-%d') for d in dates],
                'open': opens,
                'high': highs,
                'low': lows,
                'close': prices,
                'volume': volumes,
                'amount': amounts
            })
            
            print(f"生成了 {days} 天模拟历史数据")
            return df
        except Exception as e:
            print(f"生成模拟数据失败 {code}: {e}")
            return None


# 单例模式
_instance = None

def get_hybrid_source(tushare_token: Optional[str] = None) -> HybridDataSource:
    """获取混合数据源单例"""
    global _instance
    if _instance is None:
        _instance = HybridDataSource(tushare_token)
    return _instance


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("混合数据源测试")
    print("=" * 60)
    
    # 初始化（不配置token，使用免费数据源）
    ds = HybridDataSource()
    
    # 测试1: 单个股票实时行情
    print("\n测试1: 获取长江电力实时行情")
    data = ds.get_realtime_price('600900')
    if data:
        print(f"✅ {data['name']} ({data['code']})")
        print(f"   价格: ¥{data['price']:.2f}")
        print(f"   涨跌: {data['change_pct']:+.2f}%")
        print(f"   来源: {data['source']}")
    
    # 测试2: 批量查询
    print("\n测试2: 批量查询")
    codes = ['600900', '601985', '600905']
    results = ds.get_realtime_batch(codes)
    print(f"✅ 获取到 {len(results)} 只股票")
    for stock in results:
        print(f"   {stock['name']} ({stock['code']}): ¥{stock['price']:.2f} ({stock['change_pct']:+.2f}%)")
    
    # 测试3: 历史数据
    print("\n测试3: 获取历史数据")
    df = ds.get_history_data('600900', days=30)
    if df is not None:
        print(f"✅ 获取到 {len(df)} 天历史数据")
        print(df.tail())
