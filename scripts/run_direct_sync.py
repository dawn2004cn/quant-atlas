
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接运行增量同步（不通过Celery）"""

from pathlib import Path
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    print("=" * 60)
    print("TDX Dayk Incremental Sync")
    print("From: 2026-04-23 to Latest")
    print("=" * 60)

    # 创建同步服务
    service = TdxDaykSyncService()

    # 获取MySQL当前最新日期
    mysql_latest = service.get_mysql_latest_date()
    print(f"\nMySQL 当前最新日期: {mysql_latest}")
    print(f"增量同步起始日期: 2026-04-23")

    # 运行增量同步（限制处理数量用于测试）
    print("\n开始增量同步...")
    result = service.incremental_sync_from_tdx_dayk(
        start_date="2026-04-23",
        dump_qlib_bin=True,
        dump_max_workers=4,  # 减少并发数
    )

    print("\n" + "=" * 60)
    print("同步结果:")
    print("=" * 60)
    print(f"成功: {result.get('ok')}")
    print(f"模式: {result.get('mode')}")
    print(f"起始日期: {result.get('start_date')}")
    
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

    print("\n同步完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
