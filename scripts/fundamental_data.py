#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本面数据获取
"""
import akshare as ak
import pandas as pd
from cache_factory import CacheFactory

class FundamentalData:
    def __init__(self):
        self.cache = CacheFactory.get_cache()

    def get_stock_fundamental(self, code: str) -> dict:
        """
        获取单只股票的基本面数据
        """
        # 尝试从缓存获取
        cached_data = self.cache.get_fundamental_data(code)
        if cached_data:
            return cached_data

        # 获取数据
        try:
            # 使用 akshare 的股票综合指标
            stock_indicator_df = ak.stock_financial_analysis_indicator(code)
            
            # 提取关键指标
            data = {
                'pe': stock_indicator_df.get('市盈率-动态', [None])[0],
                'peg': stock_indicator_df.get('PEG', [None])[0],
                'roe': stock_indicator_df.get('净资产收益率-摊薄', [None])[0],
            }
            
            # 存入缓存
            self.cache.save_fundamental_data(code, data)
            
            return data
        except Exception as e:
            print(f"获取基本面数据失败 for {code}: {e}")
            # 返回默认值，确保策略能够继续运行
            return {
                'pe': 20.0,
                'peg': 1.0,
                'roe': 15.0
            }

    def close(self):
        """关闭资源 - 注意：不关闭共享缓存连接"""
        # 注意：不要关闭 cache，因为 CacheFactory 使用单例模式
        # self.cache.close()
        pass
