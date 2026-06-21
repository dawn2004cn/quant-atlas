# Unified Data Lake Specification

## 1. Architecture Overview
The Unified Data Lake replaces fragmented local databases with a single, structured time-series store. It is designed to be storage-agnostic, allowing the platform to scale from a local developer setup (SQLite) to a production cluster (ClickHouse/QuestDB) without changing business logic.

## 2. Core Components

### 2.1 `UnifiedDataStore` (Interface)
The abstract base class defining the contract for any storage backend:
- `fetch_data(query: DataQuery) -> pd.DataFrame`: Retrieves time-series data.
- `write_data(symbol, data, scope)`: Persists data into the lake.
- `get_health_status()`: Returns engine-specific health metrics.

### 2.2 `DataQualityFirewall` (The Validator)
A critical middleware layer that ensures "Garbage In $\neq$ Garbage Out". It performs:
- **Null Handling**: Fills NaNs via forward/backward fill or drops them in strict mode.
- **Alignment Check**: Verifies timestamp monotonicity and detects gaps in the series.
- **Outlier Detection**: Uses Z-Score analysis (threshold=5) to flag extreme price/volume anomalies.

### 2.3 `DataLakeManager` (The Coordinator)
The central entry point for all data services:
- **Storage Strategy**: Manages primary and fallback stores.
- **Pipeline**: `Store` $\rightarrow$ `Firewall` $\rightarrow$ `Business Logic`.
- **Observability**: Tracks request durations using a rolling `deque` to provide P95 latency metrics.

## 3. Data Model (Long-Format)
To support diverse data types (K-lines, Factors, Sentiment), the lake uses a **Long-Format** schema:
- `symbol`: Asset identifier.
- `market`: Market identifier (CN, US, HK).
- `timestamp`: The temporal index.
- `column_name`: The feature/metric name.
- `value`: The numeric value.
- `scope`: Data scope (REALTIME, HISTORICAL, BATCH).

This allows the platform to add new factors or data types without performing database migrations.

## 4. Migration Strategy
The `LegacyDataMigrationService` implements a heuristic-based migration:
1. **Scan**: Locate all `.db` files in the project root.
2. **Analyze**: Identify tables containing `timestamp/date` and `symbol/code` columns.
3. **Ingest**: Pivot legacy wide-format tables into the long-format lake schema.
4. **Verify**: Use the `verify_symbol` API to ensure data parity.
