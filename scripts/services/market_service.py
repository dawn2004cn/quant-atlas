#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场服务
"""

import time
import pandas as pd
from typing import List, Dict
from cache_factory import CacheFactory
from interfaces.cache_interfaces import CacheInterface


class MarketService:
    """市场服务"""
    
    def __init__(self, cache: CacheInterface = None):
        from cache_factory import SmartCacheFactory
        from enhanced_data_fetcher import get_data_fetcher
        self.cache = cache or SmartCacheFactory.get_cache(data_type='market')
        self.data_fetcher = get_data_fetcher()
        self.search_cache = {}
        self.search_cache_time = {}
    
    def get_market_overview(self, watched_stocks: List[str]) -> Dict:
        """
        获取市场总览
        
        Args:
            watched_stocks: 监控股票列表
            
        Returns:
            Dict: 市场总览数据
        """
        try:
            from market_analysis import MarketAnalysis
            stocks = []
            for code in watched_stocks:
                stock = self.cache.get_stock(code)
                if stock:
                    stocks.append(stock)
            analyzer = MarketAnalysis()
            overview = analyzer.get_market_overview(stocks)
            return overview
        except Exception as e:
            print(f"获取市场总览失败: {e}")
            return {}
    
    def get_market_all(self) -> Dict:
        """
        获取全市场股票数据
        
        Returns:
            Dict: 全市场股票数据
        """
        try:
            # 首先尝试从缓存获取数据，使用较短的缓存时间
            cached_stocks = self.cache.get_market_all_cache(max_age_minutes=30)
            
            # 如果有缓存数据，直接返回
            if cached_stocks:
                return {
                    'status': 'success', 
                    'data': cached_stocks,
                    'data_source': 'cache',
                    'async_updating': False
                }
            
            # 如果没有缓存，在线获取数据
            result = self._fetch_and_return_market_data()
            
            # 检查返回结果是否成功
            if result.get('status') == 'success' and result.get('data'):
                return result
            
            # 如果在线获取失败，尝试使用更长时间的缓存数据
            print("在线获取失败，尝试使用更长时间的缓存数据")
            cached_stocks = self.cache.get_market_all_cache(max_age_minutes=1440)  # 24小时
            if cached_stocks:
                print("使用24小时内的缓存数据")
                return {
                    'status': 'success', 
                    'data': cached_stocks,
                    'data_source': 'cache (24h fallback)',
                    'async_updating': False
                }
            
            # 如果仍然没有缓存数据，尝试使用历史缓存
            print("没有近期缓存数据，尝试使用历史缓存")
            cached_stocks = self.cache.get_market_all_cache(max_age_minutes=10080)  # 7天
            if cached_stocks:
                print("使用7天内的缓存数据")
                return {
                    'status': 'success', 
                    'data': cached_stocks,
                    'data_source': 'cache (7d fallback)',
                    'async_updating': False
                }
            
            # 如果所有尝试都失败，返回错误
            return {'status': 'error', 'message': '无法获取全市场数据，请稍后再试'}
            
        except Exception as e:
            print(f"获取全市场数据失败: {e}")
            # 尝试使用缓存数据作为备选
            try:
                # 尝试使用更长时间的缓存数据
                cached_stocks = self.cache.get_market_all_cache(max_age_minutes=1440)  # 24小时
                if cached_stocks:
                    print("发生异常，使用24小时内的缓存数据")
                    return {
                        'status': 'success', 
                        'data': cached_stocks,
                        'data_source': 'cache (24h fallback)',
                        'async_updating': False
                    }
                
                # 如果仍然没有缓存数据，尝试使用历史缓存
                cached_stocks = self.cache.get_market_all_cache(max_age_minutes=10080)  # 7天
                if cached_stocks:
                    print("发生异常，使用7天内的缓存数据")
                    return {
                        'status': 'success', 
                        'data': cached_stocks,
                        'data_source': 'cache (7d fallback)',
                        'async_updating': False
                    }
            except Exception as cache_error:
                print(f"获取缓存数据失败: {cache_error}")
                pass
            
            return {'status': 'error', 'message': f'获取全市场数据失败: {str(e)}'}
    
    def get_market_rankings(self) -> Dict:
        """
        获取市场排行榜
        
        Returns:
            Dict: 市场排行榜数据
        """
        try:
            import akshare as ak
            import pandas as pd
            import time
            from requests.exceptions import RequestException
            
            # 首先尝试从缓存获取数据
            cached_stocks = self.cache.get_market_all_cache(max_age_minutes=30)
            
            if cached_stocks:
                stocks = cached_stocks
            else:
                # 如果没有缓存，获取全市场数据
                # 添加重试机制
                max_retries = 3
                retry_interval = 2
                
                for attempt in range(max_retries):
                    try:
                        df = ak.stock_zh_a_spot_em()
                        break
                    except RequestException as e:
                        print(f"第 {attempt + 1} 次尝试获取市场数据失败: {e}")
                        if attempt < max_retries - 1:
                            print(f"等待 {retry_interval} 秒后重试...")
                            time.sleep(retry_interval)
                        else:
                            # 所有重试都失败，尝试使用旧缓存数据
                            cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)
                            if cached_stocks:
                                print("使用缓存数据作为备选")
                                stocks = cached_stocks
                            else:
                                # 没有备选数据，返回错误
                                return {'status': 'error', 'message': '获取市场数据失败'}
                
                if not cached_stocks and 'stocks' not in locals():
                    if 'df' in locals() and not df.empty:
                        # 转换为列表，处理 NaN 值
                        stocks = []
                        for _, row in df.iterrows():
                            try:
                                def safe_float(val, default=0):
                                    try:
                                        if pd.isna(val) or val is None:
                                            return default
                                        return float(val)
                                    except:
                                        return default
                                
                                price = safe_float(row['最新价'])
                                change_pct = safe_float(row['涨跌幅'])
                                amount = safe_float(row['成交额'])
                                volume = safe_float(row['成交量'])
                                turnover = safe_float(row.get('换手率', 0))
                                
                                stock = {
                                    'code': str(row['代码']),
                                    'name': str(row['名称']),
                                    'price': price,
                                    'change_pct': change_pct,
                                    'amount': amount,
                                    'volume': volume,
                                    'turnover': turnover
                                }
                                stocks.append(stock)
                            except Exception as e:
                                continue
                    else:
                        # 尝试使用旧缓存数据
                        cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)
                        if cached_stocks:
                            print("获取数据为空，使用缓存数据作为备选")
                            stocks = cached_stocks
                        else:
                            # 没有备选数据，返回错误
                            return {'status': 'error', 'message': '获取市场数据为空'}
            
            # 计算排行榜
            rankings = {
                'gainers': sorted(stocks, key=lambda x: x['change_pct'], reverse=True)[:5],
                'losers': sorted(stocks, key=lambda x: x['change_pct'])[:5],
                'amounts': sorted(stocks, key=lambda x: x['amount'], reverse=True)[:5],
                'turnovers': sorted(stocks, key=lambda x: x['turnover'], reverse=True)[:5]
            }
            
            return {
                'status': 'success', 
                'data': rankings,
                'data_source': 'cache' if cached_stocks else 'realtime' if 'df' in locals() else 'demo'
            }
            
        except Exception as e:
            print(f"获取市场排行榜失败: {e}")
            # 尝试使用缓存数据作为备选
            try:
                cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)
                if cached_stocks:
                    print("发生异常，使用缓存数据作为备选")
                    # 计算排行榜
                    rankings = {
                        'gainers': sorted(cached_stocks, key=lambda x: x['change_pct'], reverse=True)[:5],
                        'losers': sorted(cached_stocks, key=lambda x: x['change_pct'])[:5],
                        'amounts': sorted(cached_stocks, key=lambda x: x['amount'], reverse=True)[:5],
                        'turnovers': sorted(cached_stocks, key=lambda x: x['turnover'], reverse=True)[:5]
                    }
                    return {
                        'status': 'success', 
                        'data': rankings,
                        'data_source': 'cache (fallback)'
                    }
                else:
                    # 使用demo数据作为最终备选
                    print("发生异常，使用demo数据作为最终备选")
                    stocks = self._get_demo_market_data()
                    rankings = {
                        'gainers': sorted(stocks, key=lambda x: x['change_pct'], reverse=True)[:5],
                        'losers': sorted(stocks, key=lambda x: x['change_pct'])[:5],
                        'amounts': sorted(stocks, key=lambda x: x['amount'], reverse=True)[:5],
                        'turnovers': sorted(stocks, key=lambda x: x['turnover'], reverse=True)[:5]
                    }
                    return {
                        'status': 'success', 
                        'data': rankings,
                        'data_source': 'demo (fallback)'
                    }
            except:
                pass
            # 最后返回错误
            return {'status': 'error', 'message': '获取市场排行榜失败'}
    

    
    def search_stock(self, keyword: str) -> Dict:
        """
        搜索股票
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            Dict: 搜索结果
        """
        if not keyword:
            return {'status': 'error', 'message': '搜索关键词不能为空'}
        
        # 检查缓存（5分钟有效）
        import time
        now = time.time()
        if keyword in self.search_cache:
            cache_time = self.search_cache_time.get(keyword, 0)
            if now - cache_time < 300:  # 5分钟内使用缓存
                return {
                    'status': 'success',
                    'data': self.search_cache[keyword],
                    'cached': True
                }
        
        try:
            import akshare as ak
            import time
            from requests.exceptions import RequestException
            
            # 尝试获取全市场股票数据，添加重试机制
            max_retries = 3
            retry_interval = 2
            
            for attempt in range(max_retries):
                try:
                    df = ak.stock_zh_a_spot_em()
                    break
                except RequestException as e:
                    print(f"第 {attempt + 1} 次尝试搜索股票失败: {e}")
                    if attempt < max_retries - 1:
                        print(f"等待 {retry_interval} 秒后重试...")
                        time.sleep(retry_interval)
                    else:
                        # akshare失败，尝试使用腾讯实时数据接口
                        print("akshare失败，尝试使用腾讯实时数据接口...")
                        return self._search_stock_from_tencent(keyword)
            
            if df.empty:
                return {'status': 'error', 'message': '获取股票数据失败'}
            
            # 模糊搜索（代码或名称）
            mask = df['代码'].str.contains(keyword, na=False) | df['名称'].str.contains(keyword, na=False)
            results = df[mask].head(10)
            
            stocks = []
            for _, row in results.iterrows():
                try:
                    stocks.append({
                        'code': row['代码'],
                        'name': row['名称'],
                        'price': float(row['最新价']),
                        'change_pct': float(row['涨跌幅'])
                    })
                except Exception as e:
                    print(f"处理搜索结果失败: {e}")
                    continue
            
            # 缓存结果
            self.search_cache[keyword] = stocks
            self.search_cache_time[keyword] = now
            
            return {
                'status': 'success',
                'data': stocks
            }
        
        except Exception as e:
            print(f"搜索股票失败: {e}")
            # 尝试使用腾讯实时数据接口
            return self._search_stock_from_tencent(keyword)
    
    def _search_stock_from_tencent(self, keyword: str) -> Dict:
        """
        从腾讯接口搜索股票
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            Dict: 搜索结果
        """
        try:
            # 使用腾讯接口搜索股票
            import requests
            
            # 构建搜索URL
            url = f"https://smartbox.gtimg.cn/s3/?v=2&q={keyword}&t=all"
            
            resp = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            
            # 解析返回数据
            data = resp.json()
            
            if not data or 'data' not in data:
                return {'status': 'error', 'message': '未找到匹配的股票'}
            
            stocks = []
            for item in data['data']:
                try:
                    code = item.get('code', '')
                    name = item.get('name', '')
                    if code and name:
                        stocks.append({
                            'code': code,
                            'name': name,
                            'price': 0.0,  # 腾讯搜索接口不返回价格
                            'change_pct': 0.0
                        })
                except Exception as e:
                    print(f"处理搜索结果失败: {e}")
                    continue
            
            # 获取实时价格数据
            if stocks:
                codes = [stock['code'] for stock in stocks[:10]]
                realtime_data = self.data_fetcher.fetch_realtime_data(codes)
                
                for stock in stocks:
                    if stock['code'] in realtime_data:
                        data = realtime_data[stock['code']]
                        stock['price'] = data.get('price', 0.0)
                        stock['change_pct'] = data.get('change_pct', 0.0)
            
            # 缓存结果
            import time
            self.search_cache[keyword] = stocks
            self.search_cache_time[keyword] = time.time()
            
            return {
                'status': 'success',
                'data': stocks,
                'data_source': 'tencent'
            }
            
        except Exception as e:
            print(f"腾讯搜索股票失败: {e}")
            return {'status': 'error', 'message': f'搜索失败: {str(e)}'}
    
    def _fetch_and_return_market_data(self) -> Dict:
        """
        获取并返回市场数据
        
        Returns:
            Dict: 市场数据
        """
        try:
            import akshare as ak
            import pandas as pd
            import math
            import time
            from requests.exceptions import RequestException
            
            # 尝试获取全市场股票数据，添加重试机制
            max_retries = 3
            retry_interval = 2
            
            for attempt in range(max_retries):
                try:
                    # 获取全市场股票数据
                    df = ak.stock_zh_a_spot_em()
                    break
                except RequestException as e:
                    print(f"第 {attempt + 1} 次尝试获取市场数据失败: {e}")
                    if attempt < max_retries - 1:
                        print(f"等待 {retry_interval} 秒后重试...")
                        time.sleep(retry_interval)
                    else:
                        # 所有重试都失败，尝试使用缓存数据
                        cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)  # 延长缓存时间到2小时
                        if cached_stocks:
                            print("使用缓存数据作为备选")
                            return {
                                'status': 'success', 
                                'data': cached_stocks,
                                'data_source': 'cache (fallback)',
                                'async_updating': False
                            }
                        else:
                            return {'status': 'error', 'message': f'网络连接失败: {str(e)}'}
            
            if df.empty:
                # 尝试使用缓存数据作为备选
                cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)
                if cached_stocks:
                    print("获取数据为空，使用缓存数据作为备选")
                    return {
                        'status': 'success', 
                        'data': cached_stocks,
                        'data_source': 'cache (fallback)',
                        'async_updating': False
                    }
                else:
                    return {'status': 'error', 'message': '获取全市场数据失败'}
            
            # 转换为列表，处理 NaN 值
            stocks = []
            for _, row in df.iterrows():
                try:
                    # 处理可能的 NaN 值
                    def safe_float(val, default=0):
                        try:
                            if pd.isna(val) or val is None:
                                return default
                            return float(val)
                        except:
                            return default
                    
                    price = safe_float(row['最新价'])
                    change_pct = safe_float(row['涨跌幅'])
                    amount = safe_float(row['成交额'])
                    volume = safe_float(row['成交量'])
                    turnover = safe_float(row.get('换手率', 0))
                    volume_ratio = safe_float(row.get('量比', 1.0))
                    prev_close = safe_float(row.get('昨收', 0))
                    
                    # 计算涨跌额
                    change_amount = price - prev_close if prev_close > 0 else 0
                    
                    stock = {
                        'code': str(row['代码']),
                        'name': str(row['名称']),
                        'price': price,
                        'change_pct': change_pct,
                        'change_amount': change_amount,
                        'amount': amount,
                        'volume': volume,
                        'volume_ratio': volume_ratio,
                        'turnover': turnover,
                        'prev_close': prev_close,
                        'industry': str(row.get('行业', '')),
                        'amplitude': safe_float(row.get('振幅', 0)),
                        'pe': safe_float(row.get('市盈率-动态', 0)),
                        'pb': safe_float(row.get('市净率', 0)),
                        'total_market_cap': safe_float(row.get('总市值', 0)),
                        'circulating_market_cap': safe_float(row.get('流通市值', 0)),
                        'limit_up_reason': '',
                        'first_limit_up_time': '',
                        'final_limit_up_time': ''
                    }
                    stocks.append(stock)
                except Exception as e:
                    print(f"处理股票数据失败: {e}")
                    continue
            
            # 保存到缓存
            self.cache.save_market_all_cache(stocks)
            
            return {
                'status': 'success', 
                'data': stocks,
                'data_source': 'realtime',
                'async_updating': False
            }
        except Exception as e:
            print(f"获取市场数据失败: {e}")
            # 尝试使用缓存数据作为备选
            try:
                cached_stocks = self.cache.get_market_all_cache(max_age_minutes=120)
                if cached_stocks:
                    print("发生异常，使用缓存数据作为备选")
                    return {
                        'status': 'success', 
                        'data': cached_stocks,
                        'data_source': 'cache (fallback)',
                        'async_updating': False
                    }
            except:
                pass
            return {'status': 'error', 'message': f'获取市场数据失败: {str(e)}'}
