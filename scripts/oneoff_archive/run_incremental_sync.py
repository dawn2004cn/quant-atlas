#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""执行TDX日K线增量同步任务（避免锁等待超时）"""

import os
from dotenv import load_dotenv
load_dotenv()

import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from pathlib import Path
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    print("=" * 60)
    print("TDX Dayk Incremental Sync")
    print("=" * 60)
    
    # 通过创建Flask应用来初始化所有依赖
    from app import create_app
    print("正在初始化Flask应用...")
    app = create_app()
    
    print("应用初始化完成!")
    
    # 获取同步服务
    from app.core.container import container
    service = container.tdx_sync_service()
    
    # 扫描股票代码
    codes = service.scan_cn_codes_from_tdx_dayk(service._require_tdx_root())
    print(f"\n通达信股票数量: {len(codes)}")
    
    # 运行增量同步
    print("\n开始增量同步...")
    result = service.incremental_sync_from_tdx_dayk(
        dump_qlib_bin=False,
        dump_max_workers=4,
    )
    
    print("\n" + "=" * 60)
    print("同步结果:")
    print("=" * 60)
    print(f"成功: {result.get('ok')}")
    print(f"模式: {result.get('mode')}")
    
    if 'stats' in result:
        stats = result['stats']
        print(f"\n统计信息:")
        print(f"  股票总数: {stats.get('codes_total')}")
        print(f"  成功同步: {stats.get('codes_ok')}")
        print(f"  MySQL行数: {stats.get('mysql_rows')}")
        print(f"  CSV文件数: {stats.get('csv_written')}")
        print(f"  日期范围: {stats.get('date_min')} - {stats.get('date_max')}")
    
    if 'error' in result:
        print(f"\n错误: {result.get('error')}")
    
    print("\n增量同步完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
