#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据获取器接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class DataFetcherInterface(ABC):
    """数据获取器接口"""
    
    @abstractmethod
    def get_stock_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取股票历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            
        Returns:
            pd.DataFrame: 股票历史数据
        """
        pass
    
    @abstractmethod
    def fetch_fund_flow(self, code: str) -> Optional[Dict]:
        """
        获取资金流数据
        
        Args:
            code: 股票代码
            
        Returns:
            Optional[Dict]: 资金流数据
        """
        pass
    
    @abstractmethod
    def fetch_and_cache(self, codes: List[str]):
        """
        获取并缓存股票数据
        
        Args:
            codes: 股票代码列表
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        关闭资源
        """
        pass
