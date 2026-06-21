#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized A-share Data Cache Management - SQLite with WAL and Batching
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 默认使用 instance 目录下的主库
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'stock_cache.db')

class StockCache:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(StockCache, cls).__new__(cls)
        return cls._instance

    def __init__(self, db_path=DB_PATH):
        if hasattr(self, '_initialized'): return
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
        self._initialized = True
    
    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')
        return conn

    def _init_db(self):
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stocks (
                    code TEXT PRIMARY KEY,
                    name TEXT,
                    price REAL,
                    change_pct REAL,
                    volume REAL,
                    amount REAL,
                    turnover REAL,
                    update_time TIMESTAMP
                )
            ''')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_update ON stocks(update_time)')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_history (
                    stock_code TEXT,
                    date TEXT,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    amount REAL,
                    PRIMARY KEY(stock_code, date)
                )
            ''')
            conn.commit()
        finally:
            conn.close()

    def save_stocks(self, stocks_data: List[Dict]):
        if not stocks_data: return
        conn = self._connect()
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            data = [
                (s['code'], s.get('name', ''), float(s.get('price', 0) or 0), 
                 float(s.get('change_pct', 0) or 0), float(s.get('volume', 0) or 0), 
                 float(s.get('amount', 0) or 0), float(s.get('turnover', 0) or 0), now)
                for s in stocks_data
            ]
            conn.executemany('''
                INSERT OR REPLACE INTO stocks 
                (code, name, price, change_pct, volume, amount, turnover, update_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', data)
            conn.commit()
        finally:
            conn.close()

    def get_all_stocks(self, max_age_minutes=1440) -> List[Dict]:
        """激进的查询策略：优先新鲜，否则返回全部"""
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.now() - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%d %H:%M:%S")
            
            # 1. 尝试获取新鲜数据
            cursor.execute('SELECT * FROM stocks WHERE update_time > ? ORDER BY amount DESC', (cutoff,))
            rows = cursor.fetchall()
            
            # 2. 如果没新鲜的，取库里最后更新的 1000 条
            if not rows:
                cursor.execute('SELECT * FROM stocks ORDER BY update_time DESC LIMIT 1000')
                rows = cursor.fetchall()
            
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_stock_history(self, stock_code: str, limit: int = 500) -> List[Dict]:
        conn = self._connect()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM stock_history WHERE stock_code = ? ORDER BY date DESC LIMIT ?', (stock_code, limit))
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]
        finally:
            conn.close()

    def save_stock_history(self, stock_code: str, history: List[Dict]):
        if not history: return
        conn = self._connect()
        try:
            data = [
                (stock_code, h['date'], h['open'], h['high'], h['low'], h['close'], h['volume'], h.get('amount', 0))
                for h in history
            ]
            conn.executemany('INSERT OR REPLACE INTO stock_history VALUES (?,?,?,?,?,?,?,?)', data)
            conn.commit()
        finally:
            conn.close()

    def close(self): pass
