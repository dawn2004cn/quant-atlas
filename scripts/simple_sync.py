
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""运行通达信日K线增量同步"""

from pathlib import Path
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加项目根目录到路径
base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

# 直接导入我们需要的模块
try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    print("=" * 60)
    print("TDX Dayk Incremental Sync")
    print("=" * 60)

    service = TdxDaykSyncService()

    # 先获取MySQL最新日期
    latest_date = service.get_mysql_latest_date()
    print(f"\nMySQL latest date: {latest_date}")

    # 运行增量同步
    print(f"\nStarting incremental sync from {latest_date}...")
    result = service.incremental_sync_from_tdx_dayk(
        start_date=None,  # 自动从MySQL最新日期开始
        dump_qlib_bin=True,
        dump_max_workers=8,
    )

    print("\n" + "=" * 60)
    print("Sync Result:")
    print("=" * 60)
    print(f"OK: {result.get('ok')}")
    print(f"Mode: {result.get('mode')}")
    if 'start_date' in result:
        print(f"Start date: {result.get('start_date')}")
    if 'stats' in result:
        stats = result['stats']
        print(f"Stats: {stats}")
    if 'error' in result:
        print(f"Error: {result.get('error')}")

    print("\nDone!")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
