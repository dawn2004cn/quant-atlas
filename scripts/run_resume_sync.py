
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.application.services.tdx_dayk_sync_service import TdxDaykSyncService
from app.infrastructure.tdx_local.paths import resolve_tdx_root
from app.config import AppSettings
from app.core.logger import get_logger

logger = get_logger("resume_sync")

def run_resume_sync():
    print("Resuming full market synchronization...")
    service = TdxDaykSyncService()
    tdx_root = resolve_tdx_root(AppSettings.from_env().tdx_root_path)
    all_codes = service.scan_cn_codes_from_tdx_dayk(tdx_root)
    
    # Filter for SH and SZ markets
    sh_sz_codes = [c for c in all_codes if c.startswith(('sh', 'sz'))]
    print(f"Total SH/SZ codes: {len(sh_sz_codes)}")
    
    try:
        # Use incremental mode to resume where we left off
        # It will compare TDX rows with MySQL and only process what's missing
        result = service._run_sync(
            mode="incremental",
            codes=sh_sz_codes,
            filter_rows=lambda rows, stock_latest: [r for r in rows if r["date"] > stock_latest] if stock_latest else rows,
            csv_merge=True,
            dump_qlib_bin=True,
            dump_max_workers=4
        )
        
        print("\nResume Sync Result:")
        print(f"Success: {result.get('ok')}")
        if 'stats' in result:
            stats = result['stats']
            print(f"Codes Processed: {stats.get('codes_ok')}")
            print(f"MySQL Rows Added: {stats.get('mysql_rows')}")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_resume_sync()
