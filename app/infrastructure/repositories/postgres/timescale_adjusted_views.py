from __future__ import annotations

"""前/后复权物化视图（由 ``market_bars`` + ``market_adjustment_factors`` 派生）。"""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

MATVIEW_QFQ = "market_bars_qfq"
MATVIEW_HFQ = "market_bars_hfq"

# 与 ``qfq_calculator.apply_qfq_to_rows`` / ``apply_hfq_to_rows`` 对齐
SQL_CREATE_QFQ_MATVIEW = f"""
CREATE MATERIALIZED VIEW {MATVIEW_QFQ} AS
SELECT
    b.time,
    b.symbol,
    b.market,
    ROUND((b.open * COALESCE(f.factor, 1.0))::numeric, 4)::double precision AS open,
    ROUND((b.high * COALESCE(f.factor, 1.0))::numeric, 4)::double precision AS high,
    ROUND((b.low * COALESCE(f.factor, 1.0))::numeric, 4)::double precision AS low,
    ROUND((b.close * COALESCE(f.factor, 1.0))::numeric, 4)::double precision AS close,
    CASE WHEN COALESCE(f.factor, 1.0) > 0
        THEN ROUND((b.volume / COALESCE(f.factor, 1.0))::numeric, 4)::double precision
        ELSE b.volume END AS volume,
    CASE WHEN COALESCE(f.factor, 1.0) > 0
        THEN ROUND((b.amount / COALESCE(f.factor, 1.0))::numeric, 4)::double precision
        ELSE b.amount END AS amount,
    b.source
FROM market_bars b
LEFT JOIN LATERAL (
    SELECT af.factor
    FROM market_adjustment_factors af
    WHERE af.symbol = b.symbol
      AND af.market = b.market
      AND af.time <= b.time
    ORDER BY af.time DESC
    LIMIT 1
) f ON TRUE
WITH NO DATA
"""

SQL_CREATE_HFQ_MATVIEW = f"""
CREATE MATERIALIZED VIEW {MATVIEW_HFQ} AS
SELECT
    b.time,
    b.symbol,
    b.market,
    ROUND((b.open * (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision AS open,
    ROUND((b.high * (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision AS high,
    ROUND((b.low * (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision AS low,
    ROUND((b.close * (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision AS close,
    CASE WHEN (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)) > 0
        THEN ROUND((b.volume / (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision
        ELSE b.volume END AS volume,
    CASE WHEN (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)) > 0
        THEN ROUND((b.amount / (COALESCE(lat.factor, 1.0) / NULLIF(COALESCE(ff.earliest_factor, 1.0), 0)))::numeric, 4)::double precision
        ELSE b.amount END AS amount,
    b.source
FROM market_bars b
LEFT JOIN LATERAL (
    SELECT af.factor
    FROM market_adjustment_factors af
    WHERE af.symbol = b.symbol
      AND af.market = b.market
      AND af.time <= b.time
    ORDER BY af.time DESC
    LIMIT 1
) lat ON TRUE
LEFT JOIN (
    SELECT DISTINCT ON (symbol, market)
        symbol, market, factor AS earliest_factor
    FROM market_adjustment_factors
    ORDER BY symbol, market, time ASC
) ff ON ff.symbol = b.symbol AND ff.market = b.market
WITH NO DATA
"""

SQL_UNIQUE_INDEX_QFQ = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{MATVIEW_QFQ}_pk "
    f"ON {MATVIEW_QFQ} (time, symbol, market)"
)
SQL_UNIQUE_INDEX_HFQ = (
    f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{MATVIEW_HFQ}_pk "
    f"ON {MATVIEW_HFQ} (time, symbol, market)"
)


def _relation_kind(cur: Any, name: str) -> str | None:
    """``pg_class.relkind``：``r``=表，``m``=物化视图；不存在则 ``None``。"""
    cur.execute(
        """
        SELECT c.relkind
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %s
          AND n.nspname = ANY (current_schemas(false))
        LIMIT 1
        """,
        (name,),
    )
    row = cur.fetchone()
    return str(row[0]) if row else None


def drop_legacy_adjusted_tables(cur: Any) -> None:
    """旧版物理 hypertable 迁移为物化视图（勿对物化视图使用 DROP TABLE）。"""
    for name in (MATVIEW_QFQ, MATVIEW_HFQ):
        kind = _relation_kind(cur, name)
        if kind == "m":
            cur.execute(f"DROP MATERIALIZED VIEW IF EXISTS {name} CASCADE")
        elif kind == "r":
            cur.execute(f"DROP TABLE IF EXISTS {name} CASCADE")


def ensure_adjusted_materialized_views(cur: Any) -> None:
    """确保前/后复权物化视图存在；已是物化视图则保留数据不重建。"""
    for name, create_sql, index_sql in (
        (MATVIEW_QFQ, SQL_CREATE_QFQ_MATVIEW, SQL_UNIQUE_INDEX_QFQ),
        (MATVIEW_HFQ, SQL_CREATE_HFQ_MATVIEW, SQL_UNIQUE_INDEX_HFQ),
    ):
        kind = _relation_kind(cur, name)
        if kind == "m":
            cur.execute(index_sql)
            continue
        if kind == "r":
            cur.execute(f"DROP TABLE IF EXISTS {name} CASCADE")
        cur.execute(create_sql)
        cur.execute(index_sql)
    logger.info("TimescaleDB materialized views ready: %s, %s", MATVIEW_QFQ, MATVIEW_HFQ)


def refresh_adjusted_materialized_views(conn: Any, *, concurrently: bool = True) -> None:
    mode = "CONCURRENTLY " if concurrently else ""
    with conn.cursor() as cur:
        cur.execute(f"REFRESH MATERIALIZED VIEW {mode}{MATVIEW_QFQ}")
        cur.execute(f"REFRESH MATERIALIZED VIEW {mode}{MATVIEW_HFQ}")
    conn.commit()
    logger.info("Refreshed TimescaleDB matviews: %s, %s", MATVIEW_QFQ, MATVIEW_HFQ)
