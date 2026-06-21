# Quant Atlas 代码优化建议书

基于对 `app` 目录核心代码（Bootstrap, Infrastructure, Application Services）的阅读，针对性能、可维护性、稳定性及架构扩展性提出以下优化建议。

---

## 1. 基础设施层：数据库连接与持久化

### 1.1 引入数据库连接池 (Database Pooling)
-   **现状**：`mysql_client.py` 采用自定义的 `threading.local()` 实现线程内连接复用。虽避免了单次请求频繁握手，但在高并发异步任务（如 Celery Worker）场景下，难以精细控制最大连接数和空闲回收。
-   **建议**：改用 `SQLAlchemy` 或 `PyMySQL` 官方推荐的 `DBUtils.PooledDB`。
-   **收益**：提升连接稳定性，防止在高并发扫描时撑爆 MySQL `max_connections`。

### 1.2 从原生 SQL 迁移至 ORM + 迁移工具
-   **现状**：大量硬编码的 DDL 字符串（`_ALL_DDL`）和原生 `cur.execute(sql, params)` 散落在各仓库实现中。手动管理 `ALTER TABLE` 容易出错。
-   **建议**：
    -   引入 `SQLAlchemy` 模型定义数据结构。
    -   使用 `Alembic` 管理数据库版本迁移。
-   **收益**：代码更具描述性，减少 SQL 注入风险，确保开发/生产环境 Schema 高度一致。

---

## 2. 领域层与应用层：解耦与逻辑清晰度

### 2.1 彻底剥离框架依赖
-   **现状**：部分领域模型或应用服务偶尔直接引用了 Flask 的 `request` 或特定的异常类。
-   **建议**：
    -   确保 `app/domain` 目录仅包含纯 Python 对象（Plain Old Python Objects）和抽象接口。
    -   应用层异常应定义为业务异常，在表现层（Presentation）进行统一转换。
-   **收益**：逻辑可测试性更高，未来迁移至 FastStream 或 gRPC 无需重写核心业务。

### 2.2 强化 Repository 模式
-   **现状**：部分 Service（如 `SignalFlagScannerService`）内部混杂了大量数据访问和原始 DataFrame 处理逻辑。
-   **建议**：
    -   将所有底层查询收口至 `infrastructure/repositories`。
    -   提供更高抽象的查询方法（如 `find_hot_stocks_by_date`），而不是返回原始 `cur.fetchall()` 结果。
-   **收益**：Service 职责单一（单一职责原则），专注于业务编排。

---

## 3. 并发与计算优化 (Performance & Scalability)

### 3.1 深度利用分布式任务队列 (Celery)
-   **现状**：全市场扫描任务（Signal Flag）计算量大。若直接在 Web 进程执行会导致阻塞。
-   **建议**：
    -   将耗时的 Qlib 计算、Kronos 推理、多源行情爬取全部转化为异步任务。
    -   利用 Celery 的 `chunks` 或 `groups` 将 5000+ 标的的扫描拆分为多个子任务并行执行。
-   **收益**：Web 响应秒开，后台处理能力可随 Worker 节点横向扩展。

### 3.2 计算结果分级缓存
-   **现状**：目前已有了 MySQL 级缓存。
-   **建议**：
    -   对热点数据（如首页行情、实时情绪指数）引入 **Redis L1 缓存**。
    -   对 Qlib 计算好的因子数据进行本地 **Parquet 缓存**，避免重复计算。
-   **收益**：降低 MySQL IO 压力，极速提升数据读取效率。

---

## 4. 稳定性与健壮性 (Reliability)

### 4.1 统一异常拦截与告警
-   **现状**：各层 `try...except` 风格不一，部分错误信息仅打印在日志中。
-   **建议**：
    -   在表现层实现全局 `Error Handler`。
    -   核心链路（如交易 Bot 异常、LLM 挂掉）接入飞书/钉钉/邮件告警。
-   **收益**：实现系统异常的实时感知。

### 4.2 API 响应规范化
-   **现状**：`common.py` 中有 `ok_response`，但返回值结构仍有旧脚本兼容逻辑（legacy alias）。
-   **建议**：
    -   使用 `Pydantic` 定义 API 的入参验证与出参序列化模型。
    -   逐步废弃 Legacy 别名，统一输出标准 JSON 结构。
-   **收益**：前后端联调更高效，接口契约更明确。

---

## 5. 前端表现层优化

### 5.1 组件化与状态管理
-   **建议**：目前页面主要由 Flask Jinja 渲染。随着功能增加（如 Kronos 动态图表、Trading Bot 实时面板），建议向 **Vue3 / React** 这种现代框架演进，通过 REST API 通信。
-   **收益**：提升用户交互体验，支持更复杂的数据可视化。

---
*由 Quant Atlas 架构重组组提交*
*日期：2026-04-22*
