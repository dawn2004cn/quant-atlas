
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试增量同步功能"""

from pathlib import Path
import sys

base_dir = Path(__file__).parent
sys.path.insert(0, str(base_dir))

try:
    from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService

    service = TdxDaykSyncService()

    # 1. 检查MySQL最新日期
    mysql_latest = service.get_mysql_latest_date()
    print(f"MySQL最新日期: {mysql_latest}")

    # 2. 扫描通达信股票数量
    codes = service.scan_cn_codes_from_tdx_dayk(service._tdx_root)
    print(f"通达信股票数量: {len(codes)}")

    # 3. 测试单只股票同步
    if codes:
        test_code = codes[0]
        print(f"\n测试股票: {test_code}")
        
        from app.infrastructure.tdx_local.paths import TdxLocalPaths
        paths = TdxLocalPaths(service._tdx_root)
        mkt = test_code[:2]
        code6 = test_code[-6:]
        p = paths.lday_file_by_market(market=mkt, code6=code6)
        print(f"文件路径: {p}")
        print(f"文件存在: {p.exists()}")

    print("\n测试完成!")

except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
