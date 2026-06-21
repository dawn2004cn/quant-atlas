#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强型数据获取模块
集成多个数据源作为akshare的备选，提高数据获取的稳定性
"""

import yfinance as yf
import pandas as pd
import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

# 尝试导入 adata，如果未安装则忽略
try:
    import adata
    ADATA_AVAILABLE = True
except ImportError:
    ADATA_AVAILABLE = False

# 尝试导入 akshare，如果未安装则忽略
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

# 导入缓存工厂
from cache_factory import SmartCacheFactory


class EnhancedDataFetcher:
    """增强型数据获取器，支持多数据源备选"""
    
    def __init__(self, max_workers: int = 4, retry_times: int = 3):
        """
        初始化数据获取器
        
        Args:
            max_workers: 并发线程数
            retry_times: 每个数据源重试次数
        """
        self.max_workers = max_workers
        self.retry_times = retry_times
        self.session = requests.Session()
        # 初始化缓存实例
        self.redis_cache = SmartCacheFactory.get_redis_cache()
        self.sqlite_cache = SmartCacheFactory.get_sqlite_cache()
        
    def get_yahoo_ticker(self, code: str) -> str:
        """获取Yahoo Finance的股票代码格式"""
        code = str(code).zfill(6)
        if code.startswith('6'):
            return f"{code}.SS"
        elif code.startswith(('0', '3')):
            return f"{code}.SZ"
        else:
            return f"{code}.BJ"
    
    def get_tencent_full_code(self, code: str) -> str:
        """获取腾讯接口的股票代码格式"""
        code = str(code).zfill(6)
        if code.startswith('6'):
            return f"sh{code}"
        elif code.startswith(('0', '3')):
            return f"sz{code}"
        else:
            return f"bj{code}"
    
    def get_sohu_code(self, code: str) -> str:
        """获取搜狐接口的股票代码格式"""
        return f"cn_{str(code).zfill(6)}"
    
    def fetch_from_yfinance(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从Yahoo Finance获取股票数据"""
        try:
            ticker = self.get_yahoo_ticker(code)
            df = yf.download(
                tickers=ticker,
                start=start_date,
                end=end_date,
                interval="1d",
                auto_adjust=True,
                progress=False,
                timeout=20
            )
            if not df.empty and len(df) > 20:
                df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
                df.columns = ['open', 'high', 'low', 'close', 'volume']
                df = df.loc[start_date:end_date]
                return df, None
            return None, "yfinance 数据不足"
        except requests.exceptions.Timeout:
            return None, "yfinance 网络超时"
        except requests.exceptions.ConnectionError:
            return None, "yfinance 连接错误"
        except Exception as e:
            return None, f"yfinance 异常: {str(e)[:80]}"
    
    def fetch_from_tencent(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从腾讯接口获取股票数据"""
        try:
            url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?_var=kline_dayqfq&param={self.get_tencent_full_code(code)},day,,,1000,qfqa"
            resp = self.session.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            text = resp.text.strip()
            
            if "kline_dayqfq=" in text:
                json_str = text.split("kline_dayqfq=", 1)[1].strip()
                if json_str.endswith(';'):
                    json_str = json_str[:-1]
            else:
                json_str = text
            
            data = json.loads(json_str)
            kline = None
            
            if isinstance(data, dict):
                code_value = data.get("code", 1)
                msg = data.get("msg", "")
                if code_value != 0:
                    return None, f"腾讯接口错误: {msg}"
                
                data_field = data.get("data", {})
                if isinstance(data_field, dict):
                    full = self.get_tencent_full_code(code)
                    kline = data_field.get(full, {}).get("day")
                elif isinstance(data_field, list):
                    for item in data_field:
                        if isinstance(item, dict):
                            if "day" in item:
                                kline = item.get("day")
                                if kline:
                                    break
                            full = self.get_tencent_full_code(code)
                            if full in item:
                                kline = item.get(full, {}).get("day")
                                if kline:
                                    break
            
            if not kline:
                return None, "腾讯无前复权数据"
            
            if not isinstance(kline, list) or len(kline) == 0:
                return None, "腾讯返回数据格式错误"
            
            if not all(isinstance(item, list) for item in kline):
                return None, "腾讯返回数据格式错误"
            
            df = pd.DataFrame(kline, columns=['date', 'open', 'close', 'high', 'low', 'volume', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.set_index('date', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            df = df.loc[start_date:end_date]
            return df, None
            
        except requests.exceptions.Timeout:
            return None, "腾讯网络超时"
        except requests.exceptions.ConnectionError:
            return None, "腾讯连接错误"
        except json.JSONDecodeError:
            return None, "腾讯返回数据格式错误"
        except Exception as e:
            return None, f"腾讯异常: {str(e)[:80]}"
    
    def fetch_from_sohu(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从搜狐接口获取股票数据"""
        try:
            sohu_code = self.get_sohu_code(code)
            url = f"https://q.stock.sohu.com/hisHq?code={sohu_code}&start={start_date.replace('-', '')}&end={end_date.replace('-', '')}&stat=1&order=D&period=d&rt=json"
            
            resp = self.session.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            data_list = resp.json()
            
            if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
                return None, "搜狐返回空数据"
            
            hq = data_list[0].get("hq", [])
            if not hq:
                return None, "搜狐无 hq 数据"
            
            df = pd.DataFrame(hq, columns=['date', 'open', 'close', 'change', 'pct',  'low', 'high','volume', 'amount', 'turnover'])
            df['date'] = pd.to_datetime(df['date'])
            for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df.set_index('date', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            df = df.loc[start_date:end_date]
            return df, None
            
        except requests.exceptions.Timeout:
            return None, "搜狐网络超时"
        except requests.exceptions.ConnectionError:
            return None, "搜狐连接错误"
        except json.JSONDecodeError:
            return None, "搜狐返回数据格式错误"
        except Exception as e:
            return None, f"搜狐异常: {str(e)[:80]}"
    
    def fetch_from_adata(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从adata获取股票数据"""
        if not ADATA_AVAILABLE:
            return None, "adata 库未安装"
        
        try:
            df = adata.stock.market.get_market(
                stock_code=code,
                k_type=1,
                start_date=start_date,
                adjust_type=1
            )
            
            if df.empty or len(df) < 20:
                return None, "adata 数据不足"
            
            df = df.rename(columns={
                'trade_date': 'date',
                'open': 'open',
                'close': 'close',
                'high': 'high',
                'low': 'low',
                'volume': 'volume'
            })
            
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df = df[['open', 'high', 'low', 'close', 'volume']]
            df = df.loc[start_date:end_date]
            
            return df, None
        except Exception as e:
            return None, f"adata 异常: {str(e)[:80]}"
    
    def fetch_from_akshare(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从akshare获取股票数据"""
        if not AKSHARE_AVAILABLE:
            return None, "akshare 库未安装"
        
        try:
            # 确定股票市场
            code_str = str(code).zfill(6)
            if code_str.startswith('6'):
                market = 'sh'
            elif code_str.startswith(('0', '3')):
                market = 'sz'
            elif code_str.startswith(('8', '9')):  # 北交所股票
                market = 'bj'
            else:
                market = 'sh'
            
            # 构建 akshare 股票代码
            ak_code = f"{market}{code_str}"
            
            # 获取股票数据
            df = ak.stock_zh_a_hist(
                symbol=ak_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"  # 前复权
            )
            
            if df.empty or len(df) < 20:
                return None, "akshare 数据不足"
            
            # 重命名列以匹配项目格式
            df = df.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume'
            })
            
            # 转换日期格式
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 选择需要的列
            df = df[['open', 'high', 'low', 'close', 'volume']]
            
            # 确保数据范围正确
            df = df.loc[start_date:end_date]
            
            return df, None
        except Exception as e:
            return None, f"akshare 异常: {str(e)[:80]}"
    
    def fetch_from_redis_cache(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从Redis缓存获取股票数据"""
        try:
            if not self.redis_cache:
                return None, "Redis 缓存未初始化"
            
            # 从缓存获取数据
            data = self.redis_cache.get_stock_history(code)
            if not data:
                return None, "Redis 缓存无数据"
            
            # 转换为 DataFrame
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 确保数据范围正确
            df = df.loc[start_date:end_date]
            
            if df.empty:
                return None, "Redis 缓存数据范围不匹配"
            
            return df, None
        except Exception as e:
            return None, f"Redis 缓存异常: {str(e)[:80]}"
    
    def fetch_from_sqlite_cache(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """从SQLite缓存获取股票数据"""
        try:
            if not self.sqlite_cache:
                return None, "SQLite 缓存未初始化"
            
            # 从缓存获取数据
            data = self.sqlite_cache.get_stock_history(code)
            if not data:
                return None, "SQLite 缓存无数据"
            
            # 转换为 DataFrame
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            
            # 确保数据范围正确
            df = df.loc[start_date:end_date]
            
            if df.empty:
                return None, "SQLite 缓存数据范围不匹配"
            
            return df, None
        except Exception as e:
            return None, f"SQLite 缓存异常: {str(e)[:80]}"
    
    def fetch_stock_data(self, code: str, start_date: str, end_date: str) -> Tuple[Optional[pd.DataFrame], str]:
        """
        获取单只股票数据，尝试多个数据源
        
        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Tuple[Optional[pd.DataFrame], str]: (数据, 数据源名称)
        """
        # 优先尝试从缓存获取数据，然后从外部数据源获取
        sources = [
            ("akshare", lambda: self.fetch_from_akshare(code, start_date, end_date)),
            ("redis_cache", lambda: self.fetch_from_redis_cache(code, start_date, end_date)),
            ("sqlite_cache", lambda: self.fetch_from_sqlite_cache(code, start_date, end_date)),
            ("adata", lambda: self.fetch_from_adata(code, start_date, end_date)),
            ("tencent", lambda: self.fetch_from_tencent(code, start_date, end_date)),
            ("sohu", lambda: self.fetch_from_sohu(code, start_date, end_date)),
            ("yfinance", lambda: self.fetch_from_yfinance(code, start_date, end_date))
        ]
        
        results = []
        for source_name, fetch_func in sources:
            for attempt in range(self.retry_times):
                try:
                    df, err = fetch_func()
                    if df is not None and not df.empty:
                        # 对于缓存数据，只要有数据就使用
                        if source_name in ["redis_cache", "sqlite_cache"]:
                            results.append((source_name, df))
                            break
                        # 对于外部数据源，需要数据量足够
                        elif len(df) > 20:
                            # 验证数据日期范围
                            try:
                                first_date = df.index[0]
                                if pd.to_datetime(first_date) >= pd.to_datetime(start_date):
                                    results.append((source_name, df))
                                    break
                            except:
                                results.append((source_name, df))
                                break
                except Exception as e:
                    print(f"  {code} - {source_name} 尝试 {attempt+1} 失败: {str(e)[:50]}")
                time.sleep(0.5)
        
        if results:
            # 按数据源优先级和数据量排序
            # 优先级: akshare > redis_cache > sqlite_cache > adata > tencent > sohu > yfinance
            priority = {
                "akshare": 7,
                "redis_cache": 6,
                "sqlite_cache": 5,
                "adata": 4,
                "tencent": 3,
                "sohu": 2,
                "yfinance": 1
            }
            
            # 首先按优先级排序，然后按数据量排序
            results.sort(key=lambda x: (priority.get(x[0], 0), len(x[1])), reverse=True)
            best_source, best_df = results[0]
            return best_df, best_source
        
        return None, "所有数据源均失败"
    
    def fetch_multiple_stocks(self, codes: List[str], start_date: str, end_date: str) -> Dict[str, Tuple[Optional[pd.DataFrame], str]]:
        """
        并发获取多只股票数据
        
        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict[str, Tuple[Optional[pd.DataFrame], str]]: 股票代码到数据和数据源的映射
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_code = {
                executor.submit(self.fetch_stock_data, code, start_date, end_date): code 
                for code in codes
            }
            
            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    df, source = future.result()
                    results[code] = (df, source)
                except Exception as e:
                    results[code] = (None, f"异常: {str(e)[:50]}")
        
        return results
    
    def fetch_realtime_data(self, codes: List[str]) -> Dict[str, Dict]:
        """
        获取实时行情数据
        
        Args:
            codes: 股票代码列表
            
        Returns:
            Dict[str, Dict]: 股票代码到实时数据的映射
        """
        results = {}
        
        # 尝试从腾讯接口获取实时数据
        try:
            # 批量获取，每次最多50只
            batch_size = 50
            for i in range(0, len(codes), batch_size):
                batch_codes = codes[i:i+batch_size]
                code_str = ','.join([self.get_tencent_full_code(code) for code in batch_codes])
                url = f"https://qt.gtimg.cn/q={code_str}"
                
                resp = self.session.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
                resp.raise_for_status()
                
                # 解析返回数据
                lines = resp.text.strip().split(';')
                for line in lines:
                    if not line.strip():
                        continue
                    
                    # 提取股票代码和数据
                    if 'v_' in line:
                        parts = line.split('~')
                        if len(parts) >= 45:
                            code = parts[2]
                            results[code] = {
                                'code': code,
                                'name': parts[1],
                                'price': float(parts[3]),
                                'change': float(parts[4]),
                                'change_pct': float(parts[5]),
                                'volume': int(parts[6]),
                                'amount': float(parts[7]),
                                'open': float(parts[8]),
                                'high': float(parts[9]),
                                'low': float(parts[10]),
                                'pre_close': float(parts[11]),
                                'turnover': float(parts[38]) if parts[38] else 0
                            }
        except Exception as e:
            print(f"获取实时数据失败: {e}")
        
        return results
    
    def close(self):
        """关闭session"""
        self.session.close()


# 全局数据获取器实例
_data_fetcher = None

def get_data_fetcher() -> EnhancedDataFetcher:
    """获取全局数据获取器实例"""
    global _data_fetcher
    if _data_fetcher is None:
        _data_fetcher = EnhancedDataFetcher()
    return _data_fetcher
