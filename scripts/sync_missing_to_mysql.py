"""同步缺失的股票到 MySQL"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.bootstrap_components.infrastructure_binding import bind_application_infrastructure
from app.config import get_settings
import pandas as pd


def sync_missing_stocks_to_mysql():
    """同步CSV中有但MySQL中没有的股票到MySQL"""
    from app.infrastructure.repositories.common.deps import create_mysql_connection_port
    
    settings = get_settings()
    bind_application_infrastructure(settings)
    
    mysql_port = create_mysql_connection_port(settings)
    
    # 获取CSV中的股票代码
    csv_dir = Path('instance/qlib_export')
    csv_files = list(csv_dir.glob('*.csv'))
    csv_codes = {f.stem for f in csv_files}
    
    # 获取已同步到MySQL的股票代码
    conn = mysql_port.connect()
    mysql_codes = set()
    try:
        with conn.cursor() as cur:
            for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
                try:
                    cur.execute(f"SELECT DISTINCT stock_code FROM {table}")
                    for row in cur.fetchall():
                        if row[0]:
                            mysql_codes.add(str(row[0]).upper())
                except Exception:
                    pass
    finally:
        conn.close()
    
    # 找出缺失的股票
    missing = csv_codes - mysql_codes
    print(f"CSV股票数: {len(csv_codes)}")
    print(f"MySQL股票数: {len(mysql_codes)}")
    print(f"缺失股票数: {len(missing)}")
    
    if not missing:
        print("✅ 所有股票都已同步到MySQL")
        return
    
    print(f"\n开始同步 {len(missing)} 只缺失股票到MySQL...")
    
    # 同步缺失的股票
    conn = mysql_port.connect()
    synced = 0
    failed = 0
    
    try:
        for i, stock_code in enumerate(sorted(missing), 1):
            csv_path = csv_dir / f"{stock_code}.csv"
            if not csv_path.exists():
                continue
            
            try:
                df = pd.read_csv(csv_path)
                rows = df.to_dict("records")
                
                # 写入MySQL
                table = f"stock_history_{stock_code.lower()[:2]}"
                with conn.cursor() as cur:
                    for row in rows:
                        sql = f"""
                            INSERT INTO {table} (stock_code, date, open, high, low, close, volume, amount)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                open = VALUES(open), high = VALUES(high), low = VALUES(low),
                                close = VALUES(close), volume = VALUES(volume), amount = VALUES(amount)
                        """
                        cur.execute(sql, (
                            stock_code,
                            row.get('date'),
                            row.get('open'),
                            row.get('high'),
                            row.get('low'),
                            row.get('close'),
                            row.get('volume'),
                            row.get('amount')
                        ))
                    conn.commit()
                
                synced += 1
                if i % 50 == 0 or i == len(missing):
                    print(f"  进度: {i}/{len(missing)} ({synced} 成功, {failed} 失败)")
            
            except Exception as e:
                failed += 1
                if failed <= 3:
                    print(f"  ⚠️ 失败 {stock_code}: {e}")
                conn.rollback()
    
    finally:
        conn.close()
    
    print(f"\n✅ 完成: 成功 {synced}, 失败 {failed}")


if __name__ == "__main__":
    sync_missing_stocks_to_mysql()
