#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存相关接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class StockCacheInterface(ABC):
    """股票数据缓存接口"""
    
    @abstractmethod
    def get_stock(self, code: str) -> Optional[Dict]:
        """
        获取股票数据
        
        Args:
            code: 股票代码
            
        Returns:
            Optional[Dict]: 股票数据
        """
        pass
    
    @abstractmethod
    def save_stock(self, code: str, data: Dict):
        """
        保存股票数据
        
        Args:
            code: 股票代码
            data: 股票数据
        """
        pass
    
    @abstractmethod
    def save_stocks(self, stocks: List[Dict]):
        """
        批量保存股票数据
        
        Args:
            stocks: 股票数据列表
        """
        pass


class FundFlowCacheInterface(ABC):
    """资金流数据缓存接口"""
    
    @abstractmethod
    def get_fund_flow(self, code: str, max_age_hours: int = 24) -> Optional[Dict]:
        """
        获取资金流数据
        
        Args:
            code: 股票代码
            max_age_hours: 最大数据年龄（小时）
            
        Returns:
            Optional[Dict]: 资金流数据
        """
        pass
    
    @abstractmethod
    def save_fund_flow(self, code: str, data: Dict):
        """
        保存资金流数据
        
        Args:
            code: 股票代码
            data: 资金流数据
        """
        pass


class TechIndicatorsCacheInterface(ABC):
    """技术指标数据缓存接口"""
    
    @abstractmethod
    def get_tech_indicators(self, code: str, max_age_hours: int = 24) -> Optional[Dict]:
        """
        获取技术指标数据
        
        Args:
            code: 股票代码
            max_age_hours: 最大数据年龄（小时）
            
        Returns:
            Optional[Dict]: 技术指标数据
        """
        pass
    
    @abstractmethod
    def save_tech_indicators(self, code: str, data: Dict):
        """
        保存技术指标数据
        
        Args:
            code: 股票代码
            data: 技术指标数据
        """
        pass


class MarketCacheInterface(ABC):
    """市场数据缓存接口"""
    
    @abstractmethod
    def get_market_all_cache(self, max_age_minutes: int = 30) -> Optional[List[Dict]]:
        """
        获取全市场数据缓存
        
        Args:
            max_age_minutes: 最大数据年龄（分钟）
            
        Returns:
            Optional[List[Dict]]: 全市场数据
        """
        pass
    
    @abstractmethod
    def save_market_all_cache(self, data: List[Dict]):
        """
        保存全市场数据缓存
        
        Args:
            data: 全市场数据
        """
        pass


class CacheStatsInterface(ABC):
    """缓存统计接口"""
    
    @abstractmethod
    def get_cache_stats(self) -> Dict:
        """
        获取缓存统计信息
        
        Returns:
            Dict: 缓存统计信息
        """
        pass


class CacheManagementInterface(ABC):
    """缓存管理接口"""
    
    @abstractmethod
    def close(self):
        """
        关闭缓存连接
        """
        pass


class CacheInterface(StockCacheInterface, FundFlowCacheInterface, 
                   TechIndicatorsCacheInterface, MarketCacheInterface, 
                   CacheStatsInterface, CacheManagementInterface):
    """综合缓存接口"""
    pass
