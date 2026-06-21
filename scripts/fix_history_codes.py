import pymysql
import time

def get_connection():
    import os, sys
    _pw = os.environ.get("MYSQL_PASSWORD") or ""
    if not os.environ.get("MYSQL_PASSWORD"):
        print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)
    return pymysql.connect(
        host=os.environ.get("MYSQL_HOST", '192.168.8.103'),
        port=int(os.environ.get("MYSQL_PORT", "3307")),
        user=os.environ.get("MYSQL_USER", 'admin'),
        password=_pw,
        database=os.environ.get("MYSQL_DATABASE", 'quant_atlas'),
        connect_timeout=15,
        read_timeout=60,
        write_timeout=60,
        autocommit=True
    )

def fix_table(table_name, batch_size=10, max_rounds=50):
    print(f'\n=== Fixing {table_name} ===')
    total_fixed = 0
    
    for round_num in range(max_rounds):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # Get one stock code at a time to minimize lock time
            cur.execute(f'SELECT stock_code FROM {table_name} WHERE stock_code NOT LIKE "CN%%" LIMIT 1')
            row = cur.fetchone()
            
            if not row:
                print(f'  Round {round_num+1}: All fixed!')
                break
            
            code = row[0]
            
            # Check if CN: version exists
            cur.execute(f'SELECT COUNT(*) FROM {table_name} WHERE stock_code = %s', (f'CN:{code}',))
            has_cn = cur.fetchone()[0] > 0
            
            if has_cn:
                cur.execute(f'DELETE FROM {table_name} WHERE stock_code = %s', (code,))
                print(f'  Round {round_num+1}: Deleted {code}')
            else:
                cur.execute(f'UPDATE {table_name} SET stock_code = %s WHERE stock_code = %s', (f'CN:{code}', code))
                print(f'  Round {round_num+1}: Updated {code}')
            
            total_fixed += 1
            cur.close()
            conn.close()
            
            time.sleep(0.3)
            
        except Exception as e:
            print(f'  Round {round_num+1}: Error - {str(e)[:50]}')
            try:
                conn.close()
            except:
                pass
            time.sleep(1)
    
    # Final check
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(DISTINCT stock_code) FROM {table_name} WHERE stock_code NOT LIKE "CN%%"')
        remaining = cur.fetchone()[0]
        cur.close()
        conn.close()
    except:
        remaining = 'unknown'
    
    print(f'  Total fixed: {total_fixed}, Remaining: {remaining}')
    return remaining

print('Starting fix...')
remaining_sh = fix_table('stock_history_sh')
remaining_sz = fix_table('stock_history_sz')
remaining_bj = fix_table('stock_history_bj')

print(f'\n=== Final ===')
print(f'stock_history_sh: {remaining_sh} codes')
print(f'stock_history_sz: {remaining_sz} codes')
print(f'stock_history_bj: {remaining_bj} codes')
print('Done!')