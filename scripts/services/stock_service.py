#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
股票数据服务
"""

import json
import os
from typing import List, Dict
from cache_factory import CacheFactory
from interfaces.cache_interfaces import CacheInterface
from interfaces.data_fetcher_interface import DataFetcherInterface


class StockService:
    """股票数据服务"""
    
    def __init__(self, cache: CacheInterface = None, fetcher: DataFetcherInterface = None):
        from cache_factory import SmartCacheFactory
        self.cache = cache or SmartCacheFactory.get_cache(data_type='stock')
        self.history_cache = SmartCacheFactory.get_cache(data_type='history')
        if fetcher:
            self.fetcher = fetcher
        else:
            from stock_async_fetcher import StockAsyncFetcher
            self.fetcher = StockAsyncFetcher()
    
    def close(self):
        """关闭资源"""
        if hasattr(self.fetcher, 'close'):
            self.fetcher.close()
    
    def get_stocks(self, watched_stocks: List[str]) -> List[Dict]:
        """
        获取所有监控股票数据
        
        Args:
            watched_stocks: 监控股票列表
            
        Returns:
            List[Dict]: 股票数据列表
        """
        stocks = []
        for code in watched_stocks:
            stock = self.cache.get_stock(code)
            if stock:
                # 获取资金流
                fund = self.cache.get_fund_flow(code, max_age_hours=48)
                if fund:
                    stock['fund_flow'] = fund
                
                # 获取技术指标
                tech = self.cache.get_tech_indicators(code, max_age_hours=48)
                if tech:
                    stock['tech_indicators'] = tech
                
                # 添加数据来源标记
                stock['data_source'] = 'cache'
                stocks.append(stock)
        return stocks
    
    def get_stocks_realtime(self, watched_stocks: List[str]) -> List[Dict]:
        """
        获取监控股票的实时价格
        
        Args:
            watched_stocks: 监控股票列表
            
        Returns:
            List[Dict]: 股票实时数据列表
        """
        stocks = []
        for code in watched_stocks:
            stock = self.cache.get_stock(code)
            if stock:
                # 只返回关键字段，减少数据量
                stocks.append({
                    'code': stock['code'],
                    'name': stock['name'],
                    'price': stock['price'],
                    'change_pct': stock['change_pct'],
                    'turnover': stock.get('turnover', 0),
                    'update_time': stock.get('update_time'),
                    'data_source': 'cache'
                })
        return stocks
    
    def get_stock_detail(self, code: str) -> Dict:
        """
        获取单只股票详情
        
        Args:
            code: 股票代码
            
        Returns:
            Dict: 股票详情
        """
        stock = self.cache.get_stock(code)
        if not stock:
            return None
        
        # 获取资金流
        fund = self.cache.get_fund_flow(code, max_age_hours=24)
        if fund:
            stock['fund_flow'] = fund
        
        # 获取技术指标
        tech = self.cache.get_tech_indicators(code, max_age_hours=24)
        if tech:
            stock['tech_indicators'] = tech
        
        return stock
    
    def refresh_stock(self, code: str) -> bool:
        """
        刷新单只股票数据
        
        Args:
            code: 股票代码
            
        Returns:
            bool: 是否刷新成功
        """
        try:
            from tech_indicators import TechIndicatorCalculator
            
            # 1. 更新基础数据
            self.fetcher.fetch_and_cache([code])
            
            # 2. 更新技术指标
            calc = TechIndicatorCalculator()
            result = calc.calculate_indicators(code)
            if result:
                calc.cache.save_tech_indicators(code, result)
            calc.close()
            
            # 3. 更新资金流（使用智能数据源）
            self.fetcher.fetch_fund_flow(code)
            
            return True
        except Exception as e:
            print(f"后台刷新{code}失败: {e}")
            return False
    
    def close(self):
        """关闭资源"""
        if self.fetcher:
            self.fetcher.close()
