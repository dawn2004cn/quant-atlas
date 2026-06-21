"""高效批量同步CSV数据到MySQL"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings
from app.infrastructure.repositories.common.deps import create_mysql_connection_port


def sync_stocks_batch(stock_codes, mysql_port, batch_size=1000):
    """批量同步股票数据"""
    conn = mysql_port.connect()
    try:
        for i in range(0, len(stock_codes), batch_size):
            batch = stock_codes[i:i+batch_size]
            for stock_code in batch:
                csv_path = Path('instance/qlib_export') / f"{stock_code}.csv"
                if not csv_path.exists():
                    continue
                
                # 使用 LOAD DATA INFILE 方式批量导入
                table = f"stock_history_{stock_code.lower()[:2]}"
                try:
                    with conn.cursor() as cur:
                        sql = f"""
                            LOAD DATA LOCAL INFILE %s INTO TABLE {table}
                            FIELDS TERMINATED BY ',' 
                            ENCLOSED BY '"'
                            LINES TERMINATED BY '\r\n'
                            IGNORE 1 LINES
                            (stock_code, date, open, high, low, close, volume, amount)
                            ON DUPLICATE KEY UPDATE
                                open = VALUES(open), high = VALUES(high), low = VALUES(low),
                                close = VALUES(close), volume = VALUES(volume), amount = VALUES(amount)
                        """
                        cur.execute(sql, (str(csv_path),))
                    conn.commit()
                except Exception as e:
                    # 如果LOAD DATA失败，回退到逐行插入
                    try:
                        import pandas as pd
                        df = pd.read_csv(csv_path)
                        rows = df.to_dict("records")
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
                                    stock_code, row.get('date'), row.get('open'), row.get('high'),
                                    row.get('low'), row.get('close'), row.get('volume'), row.get('amount')
                                ))
                            conn.commit()
                    except Exception as fallback_e:
                        conn.rollback()
                        return False, stock_code, str(fallback_e)
        return True, None, None
    finally:
        conn.close()


def sync_missing_stocks_fast():
    """快速同步CSV中有但MySQL中没有的股票到MySQL"""
    settings = get_settings()
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
    missing = sorted(list(csv_codes - mysql_codes))
    print(f"CSV股票数: {len(csv_codes)}")
    print(f"MySQL股票数: {len(mysql_codes)}")
    print(f"缺失股票数: {len(missing)}")
    
    if not missing:
        print("✅ 所有股票都已同步到MySQL")
        return
    
    # 多线程批量同步
    num_workers = 4
    chunk_size = len(missing) // num_workers + 1
    chunks = [missing[i:i+chunk_size] for i in range(0, len(missing), chunk_size)]
    
    print(f"\n开始同步 {len(missing)} 只缺失股票到MySQL...")
    print(f"使用 {num_workers} 个线程")
    
    synced = 0
    failed = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for i, chunk in enumerate(chunks):
            futures.append(executor.submit(sync_stocks_batch, chunk, mysql_port))
        
        for i, future in enumerate(as_completed(futures)):
            result, code, error = future.result()
            if result:
                synced += len(chunks[i])
            else:
                failed.append((code, error))
            print(f"  线程 {i+1}/{num_workers} 完成: {len(chunks[i])} 只股票")
    
    print(f"\n✅ 完成: 成功 {synced}, 失败 {len(failed)}")
    if failed:
        print("失败列表:", failed[:5])


if __name__ == "__main__":
    sync_missing_stocks_fast()
