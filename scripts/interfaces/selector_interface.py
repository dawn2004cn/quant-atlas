#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
选股器接口
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class SelectorInterface(ABC):
    """选股器接口"""
    
    @abstractmethod
    def select_top_stocks(self, top_n: int, market: str) -> List[Dict]:
        """
        选择 top_n 只股票
        
        Args:
            top_n: 选择数量
            market: 市场类型
            
        Returns:
            List[Dict]: 选股结果
        """
        pass
    
    @abstractmethod
    def generate_report(self, stocks: List[Dict]) -> str:
        """
        生成选股报告
        
        Args:
            stocks: 选股结果
            
        Returns:
            str: 选股报告
        """
        pass
    
    @abstractmethod
    def close(self):
        """
        关闭资源
        """
        pass
