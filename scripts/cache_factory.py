#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
缓存工厂类 - 支持智能缓存选择和双缓存机制
"""

from config import CACHE_TYPE, REDIS_CONFIG, SQLITE_CONFIG
from interfaces.cache_interfaces import CacheInterface


class SmartCacheFactory:
    """智能缓存工厂类 - 根据数据类型和大小选择合适的缓存系统"""
    
    _instance = None
    _redis_cache = None
    _sqlite_cache = None
    
    @staticmethod
    def get_cache(data_type: str = 'default', data_size: int = 0) -> CacheInterface:
        """
        获取缓存实例（智能选择）
        
        Args:
            data_type: 数据类型 ('stock', 'history', 'user', 'market', 'default')
            data_size: 数据大小（字节）
            
        Returns:
            CacheInterface: 缓存实例
        """
        # 大数据量或高并发数据使用Redis
        if data_type in ['stock', 'history', 'market'] or data_size > 1024 * 1024:  # 大于1MB
            return SmartCacheFactory._get_redis_cache()
        # 小数据量或结构化数据使用SQLite
        else:
            return SmartCacheFactory._get_sqlite_cache()
    
    @staticmethod
    def _get_redis_cache() -> CacheInterface:
        """获取Redis缓存实例"""
        if SmartCacheFactory._redis_cache is None:
            try:
                from redis_cache import RedisCache
                SmartCacheFactory._redis_cache = RedisCache(
                    host=REDIS_CONFIG['host'],
                    port=REDIS_CONFIG['port'],
                    db=REDIS_CONFIG['db']
                )
            except Exception as e:
                print(f"[ERROR] Redis连接失败，使用SQLite作为备选: {e}")
                return SmartCacheFactory._get_sqlite_cache()
        return SmartCacheFactory._redis_cache
    
    @staticmethod
    def _get_sqlite_cache() -> CacheInterface:
        """获取SQLite缓存实例"""
        if SmartCacheFactory._sqlite_cache is None:
            try:
                from stock_cache_db import StockCache
                SmartCacheFactory._sqlite_cache = StockCache(
                    db_path=SQLITE_CONFIG['db_path']
                )
            except Exception as e:
                print(f"[ERROR] SQLite连接失败: {e}")
                raise
        return SmartCacheFactory._sqlite_cache
    
    @staticmethod
    def get_redis_cache() -> CacheInterface:
        """直接获取Redis缓存实例"""
        return SmartCacheFactory._get_redis_cache()
    
    @staticmethod
    def get_sqlite_cache() -> CacheInterface:
        """直接获取SQLite缓存实例"""
        return SmartCacheFactory._get_sqlite_cache()
    
    @staticmethod
    def close_cache():
        """关闭所有缓存连接"""
        if SmartCacheFactory._redis_cache is not None:
            SmartCacheFactory._redis_cache.close()
            SmartCacheFactory._redis_cache = None
        
        if SmartCacheFactory._sqlite_cache is not None:
            SmartCacheFactory._sqlite_cache.close()
            SmartCacheFactory._sqlite_cache = None
    
    @staticmethod
    def reset_cache():
        """重置所有缓存连接"""
        SmartCacheFactory.close_cache()


# 兼容旧接口
class CacheFactory:
    """缓存工厂类 - 兼容旧接口"""
    
    @staticmethod
    def get_cache() -> CacheInterface:
        """获取缓存实例（默认使用智能选择）"""
        return SmartCacheFactory.get_cache()
    
    @staticmethod
    def close_cache():
        """关闭缓存连接"""
        SmartCacheFactory.close_cache()
    
    @staticmethod
    def reset_cache():
        """重置缓存连接"""
        SmartCacheFactory.reset_cache()
