#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控列表服务
"""

import json
import os
from typing import List, Dict


class WatchlistService:
    """监控列表服务"""
    
    def __init__(self):
        self.watchlist_file = os.path.join(os.path.dirname(__file__), '..', 'watchlist.json')
    
    def get_watchlist(self) -> List[str]:
        """
        获取监控列表
        
        Returns:
            List[str]: 监控股票代码列表
        """
        if os.path.exists(self.watchlist_file):
            try:
                with open(self.watchlist_file, 'r', encoding='utf-8') as f:
                    stocks = json.load(f)
                    return stocks
            except:
                pass
        return []
    
    def save_watchlist(self, stocks: List[str]):
        """
        保存监控列表
        
        Args:
            stocks: 监控股票代码列表
        """
        with open(self.watchlist_file, 'w', encoding='utf-8') as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
    
    def add_to_watchlist(self, code: str, watched_stocks: List[str]) -> bool:
        """
        添加股票到监控列表
        
        Args:
            code: 股票代码
            watched_stocks: 当前监控列表
            
        Returns:
            bool: 是否添加成功
        """
        if code in watched_stocks:
            return False
        
        watched_stocks.append(code)
        self.save_watchlist(watched_stocks)
        return True
    
    def remove_from_watchlist(self, code: str, watched_stocks: List[str]) -> bool:
        """
        从监控列表移除股票
        
        Args:
            code: 股票代码
            watched_stocks: 当前监控列表
            
        Returns:
            bool: 是否移除成功
        """
        if code not in watched_stocks:
            return False
        
        watched_stocks.remove(code)
        self.save_watchlist(watched_stocks)
        return True
    
    def get_watchlist_with_info(self, watched_stocks: List[str]) -> List[Dict]:
        """
        获取监控列表及其基本信息
        
        Args:
            watched_stocks: 监控股票代码列表
            
        Returns:
            List[Dict]: 监控列表及基本信息
        """
        from cache_factory import SmartCacheFactory
        from interfaces.cache_interfaces import CacheInterface
        cache: CacheInterface = SmartCacheFactory.get_cache(data_type='stock')
        
        stocks_info = []
        for code in watched_stocks:
            stock = cache.get_stock(code)
            if stock:
                stocks_info.append({
                    'code': code,
                    'name': stock['name'],
                    'price': stock.get('price', 0),
                    'change_pct': stock.get('change_pct', 0)
                })
            else:
                stocks_info.append({
                    'code': code,
                    'name': '加载中...',
                    'price': 0,
                    'change_pct': 0
                })
        return stocks_info
