#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""执行TDX日K线全量同步任务"""

import os
from dotenv import load_dotenv
load_dotenv()

from pathlib import Path
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.core.container import container

    print("=" * 60)
    print("TDX Dayk Full Sync")
    print("=" * 60)

    service = container.tdx_sync_service()

    codes = service.scan_cn_codes_from_tdx_dayk(service._require_tdx_root())
    print(f"\n通达信股票数量: {len(codes)}")

    print("\n开始全量同步（完整模式，无limit限制）...")
    result = service.full_sync_from_tdx_dayk(
        limit=None,
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

    print("\n全量同步完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
