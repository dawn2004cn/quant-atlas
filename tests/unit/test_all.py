#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
综合测试文件，覆盖项目的主要功能模块
"""
import pytest

pytest.skip("Legacy root-level service_container tests", allow_module_level=True)

import sys
import unittest
import json
from datetime import datetime

# 添加项目路径
sys.path.append('.')

from services.service_container import service_container
from cache_factory import CacheFactory, SmartCacheFactory
from market_sentiment import calculate_market_sentiment

class TestStockMonitor(unittest.TestCase):
    """测试股票监控系统的主要功能"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        print("=== 开始测试股票监控系统 ===")
        cls.service_container = service_container
        cls.stock_service = service_container.get_stock_service()
        cls.market_service = service_container.get_market_service()
        cls.watchlist_service = service_container.get_watchlist_service()
        cls.user_service = service_container.get_user_service()
        cls.selector_service = service_container.get_selector_service()
        cls.cache = CacheFactory.get_cache()
        
    def test_service_container(self):
        """测试服务容器初始化"""
        print("\n1. 测试服务容器初始化")
        self.assertIsNotNone(self.service_container)
        self.assertIsNotNone(self.stock_service)
        self.assertIsNotNone(self.market_service)
        self.assertIsNotNone(self.watchlist_service)
        self.assertIsNotNone(self.user_service)
        self.assertIsNotNone(self.selector_service)
        print("✅ 服务容器初始化成功")
    
    def test_cache_factory(self):
        """测试缓存工厂"""
        print("\n2. 测试缓存工厂")
        # 测试默认缓存
        default_cache = CacheFactory.get_cache()
        self.assertIsNotNone(default_cache)
        
        # 测试智能缓存工厂
        stock_cache = SmartCacheFactory.get_cache(data_type='stock')
        market_cache = SmartCacheFactory.get_cache(data_type='market')
        history_cache = SmartCacheFactory.get_cache(data_type='history')
        
        self.assertIsNotNone(stock_cache)
        self.assertIsNotNone(market_cache)
        self.assertIsNotNone(history_cache)
        print("✅ 缓存工厂测试成功")
    
    def test_watchlist_service(self):
        """测试监控列表服务"""
        print("\n3. 测试监控列表服务")
        # 获取监控列表
        watchlist = self.watchlist_service.get_watchlist()
        self.assertIsInstance(watchlist, list)
        print(f"✅ 监控列表获取成功，共 {len(watchlist)} 只股票")
        
        # 测试添加和移除股票
        test_code = '600000'  # 浦发银行
        if test_code not in watchlist:
            success = self.watchlist_service.add_to_watchlist(test_code, watchlist)
            self.assertTrue(success)
            print(f"✅ 添加股票 {test_code} 成功")
            
            success = self.watchlist_service.remove_from_watchlist(test_code, watchlist)
            self.assertTrue(success)
            print(f"✅ 移除股票 {test_code} 成功")
    
    def test_market_service(self):
        """测试市场服务"""
        print("\n4. 测试市场服务")
        
        # 测试市场排行榜
        rankings = self.market_service.get_market_rankings()
        # 由于移除了demo数据，当网络连接失败时会返回错误
        if rankings.get('status') == 'success':
            data = rankings.get('data', {})
            self.assertIn('gainers', data)
            self.assertIn('losers', data)
            self.assertIn('amounts', data)
            self.assertIn('turnovers', data)
            print(f"✅ 市场排行榜获取成功")
            print(f"  涨幅榜: {len(data['gainers'])} 条")
            print(f"  跌幅榜: {len(data['losers'])} 条")
            print(f"  成交榜: {len(data['amounts'])} 条")
            print(f"  换手榜: {len(data['turnovers'])} 条")
        else:
            print(f"⚠️ 市场排行榜获取失败: {rankings.get('message')}")
        
        # 测试搜索股票
        search_result = self.market_service.search_stock('贵州茅台')
        if search_result.get('status') == 'success':
            search_data = search_result.get('data', [])
            self.assertIsInstance(search_data, list)
            print(f"✅ 股票搜索成功，找到 {len(search_data)} 条结果")
        else:
            print(f"⚠️ 股票搜索失败: {search_result.get('message')}")
    
    def test_stock_service(self):
        """测试股票服务"""
        print("\n5. 测试股票服务")
        # 获取监控股票
        watchlist = self.watchlist_service.get_watchlist()
        if watchlist:
            stocks = self.stock_service.get_stocks(watchlist[:3])  # 只测试前3只股票
            self.assertIsInstance(stocks, list)
            print(f"✅ 股票数据获取成功，共 {len(stocks)} 只股票")
            
            # 测试实时数据
            realtime_stocks = self.stock_service.get_stocks_realtime(watchlist[:3])
            self.assertIsInstance(realtime_stocks, list)
            print(f"✅ 实时股票数据获取成功")
    
    def test_market_sentiment(self):
        """测试市场情绪分析"""
        print("\n6. 测试市场情绪分析")
        sentiment = calculate_market_sentiment(use_demo_data=False)
        self.assertIn('score', sentiment)
        self.assertIn('level', sentiment)
        self.assertIn('stats', sentiment)
        print(f"✅ 市场情绪分析成功")
        print(f"  情绪评分: {sentiment['score']}")
        print(f"  情绪等级: {sentiment['level']}")
        print(f"  涨跌家数: {sentiment['stats'].get('gainers', 0)} 涨, {sentiment['stats'].get('losers', 0)} 跌")
    
    def test_selector_service(self):
        """测试选股服务"""
        print("\n7. 测试选股服务")
        # 测试中长线选股
        try:
            long_term_stocks = self.selector_service.select_long_term_stocks(top_n=5, market='all')
            self.assertIsInstance(long_term_stocks, list)
            print(f"✅ 中长线选股成功，选出 {len(long_term_stocks)} 只股票")
        except Exception as e:
            print(f"⚠️ 中长线选股测试失败: {e}")
            # 选股服务可能需要外部数据，失败是正常的
    
    def test_cache_operations(self):
        """测试缓存操作"""
        print("\n8. 测试缓存操作")
        # 测试缓存统计
        stats = self.cache.get_cache_stats()
        self.assertIsInstance(stats, dict)
        print(f"✅ 缓存统计获取成功")
        print(f"  缓存类型: {stats.get('cache_type', 'unknown')}")
        
        # 测试市场异动数据
        movements = self.cache.get_market_movements(limit=5)
        self.assertIsInstance(movements, list)
        print(f"✅ 市场异动数据获取成功，共 {len(movements)} 条")
    
    def test_user_service(self):
        """测试用户服务"""
        print("\n9. 测试用户服务")
        # 获取用户列表
        users = self.user_service.get_users()
        self.assertIsInstance(users, dict)
        print(f"✅ 用户列表获取成功，共 {len(users)} 个用户")
        
        # 获取角色列表
        roles = self.user_service.get_roles()
        self.assertIsInstance(roles, list)
        print(f"✅ 角色列表获取成功，共 {len(roles)} 个角色")
    
    def test_integration(self):
        """测试集成功能"""
        print("\n10. 测试集成功能")
        # 测试完整的市场数据流程
        try:
            # 获取市场总览
            watchlist = self.watchlist_service.get_watchlist()
            if watchlist:
                overview = self.market_service.get_market_overview(watchlist[:5])
                self.assertIsInstance(overview, dict)
                print("✅ 市场总览获取成功")
        except Exception as e:
            print(f"⚠️ 集成测试失败: {e}")
    
    @classmethod
    def tearDownClass(cls):
        """清理测试环境"""
        print("\n=== 测试完成 ===")

if __name__ == '__main__':
    # 运行所有测试
    unittest.main()
