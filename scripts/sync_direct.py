#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接执行TDX日K线增量同步（绕过容器初始化问题）"""

import os
from dotenv import load_dotenv
load_dotenv()

import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

base_dir = Path(__file__).parent.parent
sys.path.insert(0, str(base_dir))

from app.config import get_settings, BASE_DIR
from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService
from app.infrastructure.repositories.common.deps import create_default_qlib_pipeline_service

print("=" * 60)
print("TDX Dayk Direct Sync")
print("=" * 60)

settings = get_settings()
print(f"MySQL: {settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}")

qlib = create_default_qlib_pipeline_service()
service = TdxDaykSyncService(settings=settings, qlib_pipeline=qlib, base_dir=BASE_DIR)

codes = service.scan_cn_codes_from_tdx_dayk(service._require_tdx_root())
print(f"\n通达信股票数量: {len(codes)}")

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
        print(f"前5个失败: {failed[:5]}")

print("\n同步完成!")
