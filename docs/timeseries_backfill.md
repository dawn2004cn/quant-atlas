# 时序日 K 回填（TDX 为唯一数据源）

MySQL `stock_history_*` **不作为** QuestDB / ClickHouse / Timescale 的回填来源。标的与 OHLCV 均来自本地通达信 `vipdoc/*/lday/*.day`。

## 三条管道

| 管道 | 目标 | 任务 / API |
|------|------|------------|
| TDX → QuestDB + ClickHouse | `stock_history` | `timeseries-backfill`、Beat `questdb-ohlcv-after-close`、`POST /system/timeseries-ohlcv-sync` |
| TDX → Timescale | `market_bars` 等 | Beat `tdx-timescale-after-close`（需 `TIMESCALE_TDX_SYNC_BEAT=1`）、`POST /system/tdx-timescale-sync` |
| TDX → MySQL + qlib | `stock_history_*`、CSV、bin | `TDX_DAYK_CELERY_BEAT`、`POST /data/tdx-dayk/*`（**默认不写 Timescale**，见 `TDX_SYNC_ENABLE_TIMESCALE=0`） |

## 前置

1. 配置 `TDX_ROOT_PATH` 指向通达信安装目录。
2. QuestDB / ClickHouse 已建表：
   - `scripts/questdb_stock_history_ddl.sql`
   - `scripts/clickhouse_stock_history_ddl.sql`
3. `.env` 配置 `QUESTDB_*`、`CLICKHOUSE_*`；QuestDB 写入需 `pip install questdb`。
4. Timescale 需 `USE_TIMESCALEDB=1` 与 `TIMESCALEDB_*`。

## QuestDB / ClickHouse 环境变量

```env
ENABLE_TIMESERIES_SYNC=1
QUESTDB_SYNC_BEAT=1
TIMESERIES_SYNC_INCREMENTAL=1
TIMESERIES_SYNC_ALL_MARKET=1
TIMESERIES_SYNC_LIMIT=0
TIMESERIES_SYNC_MAX_SYMBOLS=50000
TIMESERIES_UPSERT_DELETE_RANGE=1
HISTORY_PREFER_TIMESERIES=1
TIMESERIES_SYNC_WORKERS=4
QUESTDB_SYNC_LOOKBACK_DAYS=1500
TIMESERIES_BACKFILL_BATCH=200
TIMESERIES_BACKFILL_MAX_BATCHES=0
```

- **Beat 增量**：`TIMESERIES_SYNC_LIMIT=0` 表示全市场；按各库 `max(trade_date)` 只补新 bar。
- **幂等**：`TIMESERIES_UPSERT_DELETE_RANGE=1` 写入前 DELETE 同标的日期区间（QuestDB/CH）；按 `date` 去重后写入；ClickHouse 建议 `ReplacingMergeTree`。
- **防漏数**：`TIMESERIES_INCREMENTAL_OVERLAP_DAYS=5` 每次增量从「各库最小最新日 − 重叠天数」重拉 TDX，覆盖修正/漏同步；QuestDB/CH 游标取 **min(latest)** 以落后库为准。
- **读链**：`HISTORY_PREFER_TIMESERIES=1` 时 CN 读顺序为 questdb → clickhouse → timescale → mysql …

`TIMESERIES_BACKFILL_MAX_BATCHES=0` 表示按 TDX 扫描结果分页直到耗尽（使用内存缓存的代码表，避免每批重扫目录）。

## Timescale 独立任务

```env
ENABLE_TIMESCALE_TDX_SYNC=1
TIMESCALE_TDX_SYNC_BEAT=1
TIMESCALE_SYNC_BEAT_HOUR=17
TIMESCALE_SYNC_BEAT_MINUTE=10
TIMESCALE_SYNC_WORKERS=4
TIMESCALE_BACKFILL_BATCH=200
TDX_SYNC_ENABLE_TIMESCALE=0
```

`TDX_SYNC_ENABLE_TIMESCALE=0` 确保常规 TDX→MySQL 日 K 任务不再附带写 Timescale。

## CLI（QuestDB + ClickHouse）

```bash
# 试跑 10 只
python -m app.cli timeseries-backfill --limit 10 --lookback-days 1500 --force

# 全市场分页回填（断点：--offset 与输出中的 next_offset）
python -m app.cli timeseries-backfill --full --lookback-days 1500 --batch-size 200

# 仅 ClickHouse
python -m app.cli timeseries-backfill --full --targets clickhouse --lookback-days 1500
```

## API（管理员）

**QuestDB + ClickHouse**

```http
POST /api/v1/system/timeseries-ohlcv-sync
Content-Type: application/json

{
  "full": true,
  "lookback_days": 1500,
  "batch_size": 200,
  "force": false
}
```

**Timescale（仅 TDX）**

```http
POST /api/v1/system/tdx-timescale-sync
Content-Type: application/json

{
  "full": true,
  "batch_size": 200,
  "offset": 0
}
```

## 分步管道（推荐：按库补跑、断点续传）

```bash
# 三库快照（行数/标的/600519 抽检）
python scripts/run_timeseries_sync_pipeline.py status

# 仅补 ClickHouse（QuestDB 已有数据时）
python scripts/run_timeseries_sync_pipeline.py sync-clickhouse

# 仅补 Timescale（workers=1，断点 instance/timescale_backfill_state.json）
python scripts/run_timeseries_sync_pipeline.py sync-timescale

# 补跑 Timescale 失败代码（instance/tdx_sync/failed_codes.txt）
python scripts/run_timeseries_sync_pipeline.py sync-failed

# 自动：status → 缺啥补啥 → verify
python scripts/run_timeseries_sync_pipeline.py run-missing
```

环境变量：`TIMESCALE_SYNC_WORKERS=1`、`TIMESCALE_BACKFILL_BATCH_SLEEP_SEC=2`、`TIMESCALE_RESUME_OK_CODES=1`。

## MySQL / CSV / qlib（与三库解耦）

```bash
python scripts/run_timeseries_sync_pipeline.py status-mysql
python scripts/run_timeseries_sync_pipeline.py sync-mysql-csv --resume --no-truncate-new
python scripts/run_timeseries_sync_pipeline.py dump-qlib --full
python scripts/run_timeseries_sync_pipeline.py run-mysql-missing
```

- 默认 ``TDX_SYNC_ENABLE_TIMESCALE=0``，只写 MySQL + ``stock_adjustment_factor`` + ``instance/qlib_export`` CSV。
- 检查点：``instance/tdx_sync/ok_codes.txt`` / ``failed_codes.txt``；灌满 ``*_new`` 后 ``--swap-tables`` 切生产表再 ``dump-qlib``。
- 亦可使用 ``scripts/run_tdx_full_sync_all.py``（等价能力更全）。

## 验证

```http
GET /api/v1/data/timeseries-health
GET /api/v1/data/timeseries-bars?symbol=600519&days=120
```

CLI：`python scripts/run_timeseries_sync_pipeline.py verify`

`source` 为 `questdb` 或 `clickhouse` 即读写链路命中。
