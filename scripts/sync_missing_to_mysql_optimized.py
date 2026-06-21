"""使用 pandas to_sql 批量同步CSV数据到MySQL（最快方式）"""
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import get_settings


def sync_stocks_pandas(stock_codes):
    """使用 pandas to_sql 批量同步股票数据"""
    import pandas as pd
    from sqlalchemy import create_engine
    
    settings = get_settings()
    db_url = f"mysql+pymysql://{settings.mysql.user}:{settings.mysql.password}@{settings.mysql.host}:{settings.mysql.port}/{settings.mysql.database}"
    engine = create_engine(db_url, pool_size=20, max_overflow=50)
    
    synced = 0
    failed = []
    
    for stock_code in stock_codes:
        csv_path = Path('instance/qlib_export') / f"{stock_code}.csv"
        if not csv_path.exists():
            continue
        
        try:
            df = pd.read_csv(csv_path)
            table = f"stock_history_{stock_code.lower()[:2]}"
            
            # 使用 to_sql 批量插入
            df.to_sql(
                name=table,
                con=engine,
                if_exists='append',
                index=False,
                chunksize=10000,
                method='multi'
            )
            synced += 1
        except Exception as e:
            failed.append((stock_code, str(e)))
    
    engine.dispose()
    return synced, failed


def sync_missing_stocks_optimized():
    """优化版同步CSV中有但MySQL中没有的股票到MySQL"""
    import pymysql
    
    settings = get_settings()
    
    # 获取CSV中的股票代码
    csv_dir = Path('instance/qlib_export')
    csv_files = list(csv_dir.glob('*.csv'))
    csv_codes = {f.stem for f in csv_files}
    
    # 获取已同步到MySQL的股票代码
    conn = pymysql.connect(
        host=settings.mysql.host,
        port=settings.mysql.port,
        user=settings.mysql.user,
        password=settings.mysql.password,
        db=settings.mysql.database
    )
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
    
    # 多线程批量同步（8个线程）
    num_workers = 8
    chunk_size = len(missing) // num_workers + 1
    chunks = [missing[i:i+chunk_size] for i in range(0, len(missing), chunk_size)]
    
    print(f"\n开始同步 {len(missing)} 只缺失股票到MySQL...")
    print(f"使用 {num_workers} 个线程，pandas to_sql 批量插入")
    
    total_synced = 0
    total_failed = []
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = []
        for chunk in chunks:
            futures.append(executor.submit(sync_stocks_pandas, chunk))
        
        for i, future in enumerate(as_completed(futures)):
            synced, failed = future.result()
            total_synced += synced
            total_failed.extend(failed)
            print(f"  线程 {i+1}/{num_workers} 完成: {synced} 成功, {len(failed)} 失败")
    
    print(f"\n✅ 完成: 成功 {total_synced}, 失败 {len(total_failed)}")
    if total_failed:
        print("失败列表:", total_failed[:3])


if __name__ == "__main__":
    sync_missing_stocks_optimized()
