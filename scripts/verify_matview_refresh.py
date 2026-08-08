"""Wait for REFRESH to complete, then verify market_bars_qfq / hfq row counts.

Monitors instance/refresh_stdout.log for completion signal, then:
1. Compares estimated row counts (reltuples, fast)
2. Runs actual COUNT with statement_timeout (falls back to estimate if timeout)
3. Spot-checks data integrity (sample rows from market_bars vs matview)
"""
import sys, os, time, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg
from app.config import get_settings

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "instance", "refresh_stdout.log")
TIMEOUT_LOG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                           "instance", "matview_refresh.log")

s = get_settings()
pg = s.database.postgres

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] {msg}", flush=True)

def connect():
    return psycopg.connect(host=pg.host, port=pg.port, user=pg.user,
                           password=pg.password, dbname=pg.database,
                           autocommit=True)

def is_refresh_running(conn):
    """Check if REFRESH MATERIALIZED VIEW is still running."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM pg_stat_activity
            WHERE datname = 'quant_atlas'
              AND pid != pg_backend_pid()
              AND state = 'active'
              AND query ILIKE '%%REFRESH MATERIALIZED VIEW%%'
        """)
        return cur.fetchone()[0] > 0

def wait_for_refresh_done(conn, max_wait=3600):
    """Wait until REFRESH is done. Checks log file + pg_stat_activity."""
    log("Waiting for REFRESH to complete...")
    start = time.time()
    check_interval = 10  # seconds

    while time.time() - start < max_wait:
        # Check 1: log file for "DONE" marker
        log_content = ""
        for path in (LOG_FILE, TIMEOUT_LOG):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    log_content += f.read()
            except FileNotFoundError:
                pass

        if "DONE:" in log_content and "QFQ" in log_content and "HFQ" in log_content:
            log("REFRESH complete (detected via log file).")
            return True

        # Check 2: pg_stat_activity (REFRESH not running anymore)
        if not is_refresh_running(conn):
            # REFRESH process is gone — check if it completed or crashed
            if "QFQ done" in log_content:
                log("REFRESH process exited, QFQ completed.")
                if "HFQ done" in log_content:
                    log("HFQ also completed.")
                    return True
                else:
                    log("HFQ not yet done — checking if still in progress...")
                    time.sleep(5)
                    if not is_refresh_running(conn):
                        log("No REFRESH running. Proceeding with verification.")
                        return True
            else:
                elapsed = int(time.time() - start)
                log(f"  REFRESH not running but no completion log yet ({elapsed}s elapsed). Waiting...")
                time.sleep(check_interval)
                continue

        elapsed = int(time.time() - start)
        # Progress: check disk space + matview size
        with conn.cursor() as cur:
            cur.execute("""
                SELECT relname,
                       pg_size_pretty(pg_total_relation_size(oid)) AS size,
                       reltuples::bigint AS est_rows
                FROM pg_class
                WHERE relname IN ('market_bars_qfq', 'market_bars_hfq')
                ORDER BY relname
            """)
            stats = cur.fetchall()
            stat_str = " | ".join(f"{r[0]}={r[1]}(~{r[2]} rows)" for r in stats)
        log(f"  [{elapsed}s] {stat_str}")
        time.sleep(check_interval)

    log(f"TIMEOUT after {max_wait}s — REFRESH may still be running.")
    return False

def get_estimated_count(conn, table_name):
    """Fast row count estimate from pg_class.reltuples (after ANALYZE)."""
    with conn.cursor() as cur:
        cur.execute("SELECT reltuples::bigint FROM pg_class WHERE relname = %s", (table_name,))
        result = cur.fetchone()
        return result[0] if result else -1

def get_actual_count(conn, table_name, timeout_ms=120000):
    """Actual COUNT(*) with statement_timeout. Returns (count, timed_out)."""
    with conn.cursor() as cur:
        cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cur.fetchone()[0], False
        except psycopg.errors.QueryCanceled:
            return -1, True

def spot_check(conn, symbol, market, limit=5):
    """Compare rows between market_bars and market_bars_qfq for a symbol."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT b.time, b.close, q.close AS qfq_close, h.close AS hfq_close
            FROM market_bars b
            LEFT JOIN market_bars_qfq q USING (time, symbol, market)
            LEFT JOIN market_bars_hfq h USING (time, symbol, market)
            WHERE b.symbol = %s AND b.market = %s
            ORDER BY b.time DESC
            LIMIT %s
        """, (symbol, market, limit))
        return cur.fetchall()

def main():
    log("=" * 60)
    log("Matview REFRESH Verification Script")
    log(f"Target: {pg.host}:{pg.port}/{pg.database}")
    log("=" * 60)

    conn = connect()

    # Phase 1: Wait for REFRESH to complete
    done = wait_for_refresh_done(conn, max_wait=3600)
    if not done:
        log("WARNING: REFRESH may not be complete. Running verification anyway.")

    # Phase 2: Ensure ANALYZE has run for accurate estimates
    log("\n=== Running ANALYZE on matviews ===")
    with conn.cursor() as cur:
        cur.execute("ANALYZE market_bars_qfq")
        log("  market_bars_qfq analyzed")
        cur.execute("ANALYZE market_bars_hfq")
        log("  market_bars_hfq analyzed")

    # Phase 3: Estimated row counts (fast)
    log("\n=== Estimated row counts (pg_class.reltuples) ===")
    bars_est = get_estimated_count(conn, "market_bars")
    qfq_est = get_estimated_count(conn, "market_bars_qfq")
    hfq_est = get_estimated_count(conn, "market_bars_hfq")
    log(f"  market_bars:     ~{bars_est:>12,} rows")
    log(f"  market_bars_qfq: ~{qfq_est:>12,} rows")
    log(f"  market_bars_hfq: ~{hfq_est:>12,} rows")

    if bars_est > 0 and qfq_est > 0:
        diff_pct = abs(bars_est - qfq_est) / bars_est * 100
        if diff_pct < 1:
            log(f"  ✅ Estimate match (diff < 1%): bars vs qfq")
        else:
            log(f"  ⚠️ Estimate diff {diff_pct:.1f}%: bars={bars_est:,} vs qfq={qfq_est:,}")
    else:
        log(f"  ⚠️ Estimates not available (need ANALYZE). bars_est={bars_est}, qfq_est={qfq_est}")

    # Phase 4: Actual COUNT (with timeout, may be slow on hypertable)
    log("\n=== Actual COUNT (with 2min timeout) ===")
    log("  Counting market_bars_qfq...")
    qfq_count, qfq_timeout = get_actual_count(conn, "market_bars_qfq", 120000)
    if qfq_timeout:
        log(f"  market_bars_qfq: COUNT timed out (using estimate: ~{qfq_est:,})")
    else:
        log(f"  market_bars_qfq: {qfq_count:,} rows")

    log("  Counting market_bars_hfq...")
    hfq_count, hfq_timeout = get_actual_count(conn, "market_bars_hfq", 120000)
    if hfq_timeout:
        log(f"  market_bars_hfq: COUNT timed out (using estimate: ~{hfq_est:,})")
    else:
        log(f"  market_bars_hfq: {hfq_count:,} rows")

    # market_bars COUNT is very slow (hypertable, 1841 chunks) — use estimate
    log(f"  market_bars:     using estimate ~{bars_est:,} (actual COUNT skipped — too slow on hypertable)")

    # Compare
    log("\n=== Comparison ===")
    if not qfq_timeout and not hfq_timeout:
        if qfq_count == hfq_count and qfq_count > 0:
            log(f"  ✅ QFQ == HFQ: {qfq_count:,} rows each")
        else:
            log(f"  ⚠️ QFQ={qfq_count:,} vs HFQ={hfq_count:,}")
    else:
        if qfq_est > 0 and abs(qfq_est - hfq_est) < max(qfq_est, 1) * 0.01:
            log(f"  ✅ Estimates match: QFQ ~{qfq_est:,} ≈ HFQ ~{hfq_est:,}")
        else:
            log(f"  ⚠️ Estimate mismatch: QFQ ~{qfq_est:,} vs HFQ ~{hfq_est:,}")

    # Phase 5: Spot-check data integrity
    log("\n=== Spot-check: 600000.SH (latest 5 rows) ===")
    rows = spot_check(conn, "600000", "SH", 5)
    if rows:
        log(f"  {'time':12s} {'raw_close':>12s} {'qfq_close':>12s} {'hfq_close':>12s} {'match':>6s}")
        for r in rows:
            match = "✅" if (r[1] == r[2] == r[3]) else "⚠️"
            log(f"  {str(r[0]):12s} {r[1]:>12.4f} {str(r[2]):>12s} {str(r[3]):>12s} {match:>6s}")
    else:
        log("  (no rows found for 600000.SH — data may not be populated yet)")

    # Phase 6: Disk space check
    log("\n=== Disk space ===")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT relname,
                   pg_size_pretty(pg_total_relation_size(oid)) AS total_size
            FROM pg_class
            WHERE relname IN ('market_bars', 'market_bars_qfq', 'market_bars_hfq')
            ORDER BY relname
        """)
        for r in cur.fetchall():
            log(f"  {r[0]:25s} {r[1]}")

    # Final verdict
    log("\n" + "=" * 60)
    all_good = True
    if qfq_est <= 0:
        log("❌ market_bars_qfq is EMPTY — REFRESH may have failed")
        all_good = False
    elif qfq_est > 0 and bars_est > 0 and abs(qfq_est - bars_est) / max(bars_est, 1) > 0.05:
        log(f"❌ Row count mismatch: bars ~{bars_est:,} vs qfq ~{qfq_est:,}")
        all_good = False
    else:
        log("✅ market_bars_qfq populated successfully")

    if hfq_est <= 0:
        log("❌ market_bars_hfq is EMPTY — REFRESH may have failed")
        all_good = False
    elif hfq_est > 0 and qfq_est > 0 and abs(hfq_est - qfq_est) / max(qfq_est, 1) > 0.05:
        log(f"❌ Row count mismatch: qfq ~{qfq_est:,} vs hfq ~{hfq_est:,}")
        all_good = False
    else:
        log("✅ market_bars_hfq populated successfully")

    if all_good:
        log("\n🎉 ALL VERIFICATIONS PASSED")
    else:
        log("\n⚠️ SOME CHECKS FAILED — review output above")
    log("=" * 60)

    conn.close()
    log(f"Done at {time.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
