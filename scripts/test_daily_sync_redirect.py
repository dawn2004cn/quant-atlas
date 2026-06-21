
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试每日同步是否正确重定向到增量同步"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    print("=" * 60)
    print("测试每日同步重定向到增量同步")
    print("=" * 60)

    service = TdxDaykSyncService()

    # 测试每日同步
    print("\n调用 daily_sync_from_tdx_dayk...")
    result = service.daily_sync_from_tdx_dayk(
        trade_date="2026-05-02",
        dump_qlib_bin=False,
    )

    print("\n每日同步结果:")
    print(f"  ok: {result.get('ok')}")
    print(f"  mode: {result.get('mode')}")
    print(f"  trade_date: {result.get('trade_date')}")
    if 'stats' in result:
        stats = result['stats']
        print(f"  同步统计:")
        print(f"    股票总数: {stats.get('codes_total')}")
        print(f"    成功同步: {stats.get('codes_ok')}")
        print(f"    MySQL行数: {stats.get('mysql_rows')}")
        print(f"    CSV文件数: {stats.get('csv_written')}")

    print("\n" + "=" * 60)
    print("测试完成！")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
