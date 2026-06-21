"""修复 stock_history_bj 表中的 stock_code 格式。

当前问题：
- stock_history_sh 使用 CN:sh000001 格式
- stock_history_sz 使用 CN:sz000001 格式
- stock_history_bj 使用 bj430017 格式 (缺少 CN: 前缀)

此脚本将 bj430017 转换为 CN:bj430017
"""

import pymysql
import time

import os, sys
DB_CONFIG = {
    'host': os.environ.get("MYSQL_HOST", '192.168.8.103'),
    'port': int(os.environ.get("MYSQL_PORT", "3307")),
    'user': os.environ.get("MYSQL_USER", 'admin'),
    'password': os.environ.get("MYSQL_PASSWORD") or "",
    'database': os.environ.get("MYSQL_DATABASE", 'quant_atlas'),
    'connect_timeout': 10,
    'read_timeout': 60,
    'write_timeout': 60,
    'autocommit': False
}
if not os.environ.get("MYSQL_PASSWORD"):
    print("WARNING: Using default DB password. Set MYSQL_PASSWORD env var.", file=sys.stderr)

def get_connection():
    return pymysql.connect(**DB_CONFIG)

def check_bj_codes():
    """检查当前 BJ 表的代码格式"""
    conn = get_connection()
    cur = conn.cursor()
    
    print("=== 检查 stock_history_bj 表 ===")
    
    # 获取样本
    cur.execute("SELECT DISTINCT stock_code FROM stock_history_bj LIMIT 10")
    samples = [r[0] for r in cur.fetchall()]
    print(f"样本代码: {samples}")
    
    # 统计格式
    cur.execute("SELECT COUNT(*) FROM stock_history_bj WHERE stock_code LIKE 'CN:%'")
    with_cn = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM stock_history_bj WHERE stock_code NOT LIKE 'CN:%'")
    no_cn = cur.fetchone()[0]
    
    print(f"带 CN: 前缀: {with_cn}")
    print(f"不带 CN: 前缀: {no_cn}")
    
    cur.close()
    conn.close()
    return no_cn > 0

def fix_bj_codes(batch_size=50, max_rounds=500):
    """修复 BJ 表的代码格式"""
    print("\n=== 开始修复 stock_history_bj ===")
    
    total_fixed = 0
    
    for round_num in range(max_rounds):
        try:
            conn = get_connection()
            cur = conn.cursor()
            
            # 获取一个不带 CN: 前缀的代码
            cur.execute(
                "SELECT stock_code FROM stock_history_bj WHERE stock_code NOT LIKE 'CN%%' LIMIT 1"
            )
            row = cur.fetchone()
            
            if not row:
                print(f"  第 {round_num+1} 轮: 全部修复完成!")
                cur.close()
                conn.close()
                break
            
            old_code = row[0]
            new_code = f"CN:{old_code}"
            
            # 检查 CN: 版本是否已存在
            cur.execute(
                "SELECT COUNT(*) FROM stock_history_bj WHERE stock_code = %s",
                (new_code,)
            )
            exists = cur.fetchone()[0] > 0
            
            if exists:
                # 如果 CN: 版本已存在，删除旧版本
                cur.execute(
                    "DELETE FROM stock_history_bj WHERE stock_code = %s",
                    (old_code,)
                )
                affected = cur.rowcount
                conn.commit()
                if round_num % 10 == 0:
                    print(f"  第 {round_num+1} 轮: 删除重复 {old_code} ({affected} 行)")
            else:
                # 否则更新为 CN: 格式
                cur.execute(
                    "UPDATE stock_history_bj SET stock_code = %s WHERE stock_code = %s",
                    (new_code, old_code)
                )
                affected = cur.rowcount
                conn.commit()
                if round_num % 10 == 0:
                    print(f"  第 {round_num+1} 轮: 更新 {old_code} -> {new_code} ({affected} 行)")
            
            total_fixed += affected
            cur.close()
            conn.close()
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  第 {round_num+1} 轮: 错误 - {str(e)[:80]}")
            try:
                conn.rollback()
                conn.close()
            except:
                pass
            time.sleep(1)
    
    # 最终检查
    print(f"\n=== 修复完成 ===")
    print(f"总共修复: {total_fixed} 行")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM stock_history_bj WHERE stock_code NOT LIKE 'CN%%'")
    remaining = cur.fetchone()[0]
    cur.close()
    conn.close()
    
    print(f"剩余未修复: {remaining}")
    return remaining

def verify_fix():
    """验证修复结果"""
    print("\n=== 验证修复结果 ===")
    
    conn = get_connection()
    cur = conn.cursor()
    
    for table in ['stock_history_sh', 'stock_history_sz', 'stock_history_bj']:
        cur.execute(f"SELECT DISTINCT stock_code FROM {table} LIMIT 3")
        samples = [r[0] for r in cur.fetchall()]
        print(f"{table}: {samples}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    print("BJ 表 stock_code 格式修复工具")
    print("=" * 40)
    
    needs_fix = check_bj_codes()
    
    if needs_fix:
        print("\n自动开始修复...")
        remaining = fix_bj_codes()
        if remaining == 0:
            verify_fix()
            print("\n修复成功!")
        else:
            print(f"\n修复完成，但仍有 {remaining} 行未修复")
    else:
        print("\nBJ 表格式已正确，无需修复")
        verify_fix()
