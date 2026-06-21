"""检查通达信数据源最新日期"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.infrastructure.external.tdx_manager import TdxManager

settings = get_settings()
print(f"TDX路径: {settings.tdx.dayk_path}", flush=True)

tdx = TdxManager(settings)
codes = tdx.scan_codes('SH')
if codes:
    print(f"上海市场股票数: {len(codes)}", flush=True)
    print(f"前5只: {codes[:5]}", flush=True)
    
    bars = tdx.get_dayk('SH000001')
    if bars is not None and len(bars) > 0:
        latest_date = bars[-1][0] if isinstance(bars[0], (list, tuple)) else bars[-1]['date']
        print(f"\n上证指数最新日期: {latest_date}", flush=True)
