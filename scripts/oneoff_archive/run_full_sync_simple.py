#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""执行TDX日K线全量同步任务（简化版，不使用容器）"""

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
    # 直接创建服务，不使用容器
    from app.config import AppSettings, BASE_DIR
    settings = AppSettings.from_env()
    
    print("=" * 60)
    print("TDX Dayk Full Sync (Simple)")
    print("=" * 60)
    
    print(f"TDX路径: {settings.tdx_root_path}")
    print(f"MySQL: {settings.database_uri}")
    
    # 初始化MySQL连接端口
    from app.modules.data.services.mysql_access import bind_mysql_connection_port
    from app.infrastructure.database.mysql_connection_adapter import MySQLConnectionAdapter
    
    mysql_adapter = MySQLConnectionAdapter(settings.mysql)
    bind_mysql_connection_port(mysql_adapter)
    print("MySQL连接端口已初始化")
    
    # 检查通达信路径
    from app.infrastructure.tdx_local.paths import TdxLocalPaths, resolve_tdx_root
    tdx_root = resolve_tdx_root(settings.tdx_root_path)
    if not tdx_root:
        print("错误：无法找到通达信路径")
        sys.exit(1)
    
    # 创建同步服务（直接导入，不通过容器）
    from app.modules.data.services.tdx_dayk_sync_service import TdxDaykSyncService
    
    # 创建QlibPipelineService（简化版本）
    from app.modules.data.services.qlib_pipeline_service import QlibPipelineService
    from app.infrastructure.repositories.basic_market_data_repository import BasicMarketDataRepository
    
    data_access = BasicMarketDataRepository()
    qlib_pipeline = QlibPipelineService(
        data_access=data_access,
        base_dir=BASE_DIR,
        tdx_root_path=settings.tdx_root_path
    )
    
    # 创建同步服务
    service = TdxDaykSyncService(
        settings=settings,
        qlib_pipeline=qlib_pipeline
    )
    
    # 扫描股票代码
    codes = service.scan_cn_codes_from_tdx_dayk(tdx_root)
    print(f"\n通达信股票数量: {len(codes)}")
    
    # 运行全量同步（无limit限制）
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
