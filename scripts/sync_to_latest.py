"""增量同步通达信数据到MySQL、CSV（到2026-06-12）"""
import os
from dotenv import load_dotenv
load_dotenv()

import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)

base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))

from app.config import get_settings, BASE_DIR
from app.application.services.data.tdx_dayk_sync_service import TdxDaykSyncService

print("=" * 60)
print("增量同步到 2026-06-12")
print("=" * 60)

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}")

service = TdxDaykSyncService(settings=settings, qlib_pipeline=None, base_dir=BASE_DIR)

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

if 'failed_codes' in result:
    failed = result['failed_codes']
    if failed:
        print(f"\n失败数量: {len(failed)}")

print("\n同步完成!")
