#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服务容器
"""

from services.stock_service import StockService
from services.watchlist_service import WatchlistService
from services.user_service import UserService
from services.market_service import MarketService
from services.selector_service import SelectorService
from cache_factory import CacheFactory
from interfaces.cache_interfaces import CacheInterface
from interfaces.data_fetcher_interface import DataFetcherInterface


class ServiceContainer:
    """服务容器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceContainer, cls).__new__(cls)
            cls._instance._init_services()
        return cls._instance
    
    def _init_services(self):
        """初始化服务"""
        # 初始化缓存
        from cache_factory import SmartCacheFactory
        
        # 根据服务类型选择合适的缓存
        self.stock_cache = SmartCacheFactory.get_cache(data_type='stock')
        self.market_cache = SmartCacheFactory.get_cache(data_type='market')
        self.history_cache = SmartCacheFactory.get_cache(data_type='history')
        self.user_cache = SmartCacheFactory.get_cache(data_type='user')
        
        # 初始化服务
        self.stock_service = StockService(cache=self.stock_cache)
        self.watchlist_service = WatchlistService()
        self.user_service = UserService()
        self.market_service = MarketService(cache=self.market_cache)
        self.selector_service = SelectorService()
    
    def get_cache(self, data_type: str = 'default', data_size: int = 0):
        """获取指定类型的缓存"""
        from cache_factory import SmartCacheFactory
        return SmartCacheFactory.get_cache(data_type, data_size)
    
    def get_stock_service(self) -> StockService:
        """获取股票服务"""
        return self.stock_service
    
    def get_watchlist_service(self) -> WatchlistService:
        """获取监控列表服务"""
        return self.watchlist_service
    
    def get_user_service(self) -> UserService:
        """获取用户服务"""
        return self.user_service
    
    def get_market_service(self) -> MarketService:
        """获取市场服务"""
        return self.market_service
    
    def get_selector_service(self) -> SelectorService:
        """获取选股服务"""
        return self.selector_service
    
    def get_cache(self) -> CacheInterface:
        """获取缓存"""
        return self.cache
    
    def close(self):
        """关闭服务"""
        # 关闭股票服务
        if hasattr(self.stock_service, 'close'):
            self.stock_service.close()
        
        # 关闭缓存
        CacheFactory.close_cache()


# 创建服务容器实例
service_container = ServiceContainer()
