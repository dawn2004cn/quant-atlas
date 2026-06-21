#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Legacy script configuration."""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
os.makedirs(INSTANCE_DIR, exist_ok=True)

# Cache backend preference for legacy scripts.
CACHE_TYPE = 'redis'

REDIS_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
}

# Use a dedicated SQLite file under instance/ to avoid the damaged legacy DB.
SQLITE_CONFIG = {
    'db_path': os.path.join(INSTANCE_DIR, 'legacy_stock_cache.db'),
}

HISTORY_DATA_DIR = 'stock_history_data'
CACHE_EXPIRY_MINUTES = 30
HISTORY_DATA_YEARS = 3

TDX_ROOT_PATH = r"E:\\tdx\\通达信金融终端(开心果交易版)V2024.02"
