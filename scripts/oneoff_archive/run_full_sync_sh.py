#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""执行TDX日K线全量同步任务（只同步sh开头的股票）"""

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
    print("TDX Dayk Full Sync (SH Only)")
    print("=" * 60)
    
    # 通过创建Flask应用来初始化所有依赖
    from app import create_app
    print("正在初始化Flask应用...")
    app = create_app()
    
    print("应用初始化完成!")
    
    # 获取同步服务
    from app.core.container import container
    service = container.tdx_sync_service()
    
    # 扫描股票代码，只保留sh开头的
    all_codes = service.scan_cn_codes_from_tdx_dayk(service._require_tdx_root())
    codes = [c for c in all_codes if c.startswith('sh')]
    print(f"\n通达信股票总数: {len(all_codes)}")
    print(f"sh开头股票数: {len(codes)}")
    
    # 定义过滤函数（全量同步，不过滤数据）
    def filter_all(rows, latest):
        return rows
    
    # 直接调用 _run_sync 方法，只同步sh股票
    print("\n开始全量同步（只同步sh股票）...")
    result = service._run_sync(
        mode="full_sh",
        codes=codes,
        filter_rows=filter_all,
        csv_merge=False,
        dump_qlib_bin=False,
        dump_max_workers=4,
        adjust_type="forward",
        skip_latest_dates=True,
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
    
    print("\n全量同步完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
