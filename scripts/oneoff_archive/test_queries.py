#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试 list_history_stock_codes 查询"""

import sys
from pathlib import Path
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv
load_dotenv()

from app.infrastructure.repositories.common.deps import create_default_qlib_pipeline_service

svc = create_default_qlib_pipeline_service()

from app.modules.system.services.helpers.tdx_data_repository_access import require_tdx_dayk_write_port
repo = require_tdx_dayk_write_port()

# 测试1: 获取股票代码
print("测试1: list_history_stock_codes()")
codes = repo.list_history_stock_codes()
print(f"  总股票数: {len(codes)}")
print(f"  前10个: {codes[:10]}")
print(f"  后10个: {codes[-10:]}")

# 测试2: 获取日期
print("\n测试2: list_history_calendar_dates()")
dates = repo.list_history_calendar_dates()
print(f"  总日期数: {len(dates)}")
print(f"  前10个: {dates[:10]}")
print(f"  后10个: {dates[-10:]}")

# 测试3: 带limit的查询
print("\n测试3: list_history_stock_codes(limit=100)")
codes_100 = repo.list_history_stock_codes(limit=100)
print(f"  股票数: {len(codes_100)}")
print(f"  前10个: {codes_100[:10]}")

print("\n✅ 所有测试完成!")
