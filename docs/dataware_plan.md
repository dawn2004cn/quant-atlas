Quant Atlas 数据层设计方案（2026 年生产级推荐）
以下是为 Quant Atlas 量身定制的数据层完整设计方案，严格遵循 Clean Architecture（DDD） 原则，将数据层置于 Infrastructure 层，并向上层（Application / Domain）提供稳定、统一的抽象。
1. 数据层整体架构
plaintextInfrastructure Layer (Data)
├── Data Sources (External)
├── Data Ingestion & ETL Pipeline (Celery + Airflow)
├── Storage Layer
│   ├── Raw Data Lake
│   ├── Structured Data (PostgreSQL + TimescaleDB)
│   ├── Time-Series Optimized (QuestDB / ClickHouse)
│   ├── Vector Store (pgvector / Milvus)
│   └── Cache (Redis)
├── Data Access Layer (Repository Pattern)
├── Data Quality & Governance
└── Unified Facade (ToolFacadeService / DataService)
核心设计原则：

分层存储：冷热分离、结构化与非结构化分离
高性能优先：回测和实时行情必须极致快
可扩展性：易于增加港股、美股、Crypto、韩股
数据一致性与可追溯：所有数据有来源、版本、采集时间
容错与降级：多源自动切换

2. 数据分类与存储选型





















































数据类型特点推荐存储方案理由行情数据 (OHLCV, Tick, 1min~月线)高频、高量、时序强TimescaleDB (PostgreSQL 扩展) + QuestDB（高频）时序优化、连续聚合查询极快基本面数据 (财报、公告、龙虎榜)结构化、低频更新PostgreSQL 主库事务性强、关系复杂因子与特征数据宽表、海量ClickHouse 或 QuestDB列式存储，适合因子挖掘AI 向量数据 (研报、新闻、对话嵌入)非结构化、向量检索pgvector (PostgreSQL) 或 Milvus与主库集成方便自选股、持仓、用户操作日志高并发读写PostgreSQL + Redis 缓存事务 + 速度回测结果、报告中等量、JSON 为主PostgreSQL + S3/MinIO持久化 + 文件分离原始数据归档海量、很少访问MinIO (S3) 或本地文件系统成本低、可追溯
推荐主数据库组合（性价比最高）：

PostgreSQL 16 + TimescaleDB（核心）
Redis 7（缓存 + 实时行情）
QuestDB 或 ClickHouse（高频行情 & 因子回测）
MinIO（原始数据归档）

3. 数据模型设计（核心实体示例）
Python# 统一 Ticker 标准化
class Ticker(Base):
    symbol = Column(String, primary_key=True)   # 600519.SH
    name = Column(String)
    market = Column(String)                     # A, HK, US, Crypto
    asset_type = Column(String)

# 时序行情（TimescaleDB hypertable）
class Bar(Base):
    __tablename__ = "bars"
    __table_args__ = ({"timescaledb_hypertable": {"time_column": "timestamp"}})
    
    timestamp = Column(DateTime(timezone=True), primary_key=True)
    ticker = Column(String, ForeignKey("ticker.symbol"))
    open = Column(Decimal)
    high = Column(Decimal)
    low = Column(Decimal)
    close = Column(Decimal)
    volume = Column(BigInteger)
    amount = Column(Decimal)          # 成交额
    source = Column(String)           # akshare, tdx, tencent
其他重要模型：

FundamentalSnapshot（财报快照）
IndustryChain（产业链映射）
FactorLibrary（因子定义与计算结果）
WatchlistGroup（自选股分组）
AuditLog（用户操作审计）

4. 数据采集与 ETL 管道
分层设计：

Collector Layer：多源采集器（AkShare、TDX 本地解析、腾讯接口等）
Normalizer：统一 Ticker、字段、单位、复权处理
Validator & Cleaner：缺失值处理、异常检测、价格跳空校验
Loader：增量写入 + 物化视图刷新
Scheduler：Celery Beat + Airflow（复杂依赖任务）

关键机制：

多源优先级 + 自动降级（TDX > AkShare > Tencent）
增量更新 + 全量重刷 双模式
数据版本控制（每次重大调整保留历史版本）

5. 数据访问层设计（Repository Pattern）
Python# 推荐实现
class BarRepository:
    async def get_bars(self, ticker: str, start: datetime, end: datetime, 
                      interval: str = "1d", source_preference: list = None) -> List[Bar]:
        # 自动走缓存 → TimescaleDB → QuestDB 降级
    
class UnifiedDataFacade:          # 向上层提供的统一门面
    async def get_market_data(...)
    async def get_fundamental(...)
    async def get_factor_data(...)
    async def batch_get_bars(...)   # 批量优化，供回测使用
ToolFacadeService 应调用此层，避免上层直接依赖具体数据库。
6. 缓存与性能优化策略

Redis：
实时行情（最新价、盘口）
热门自选股列表
常用因子计算结果（TTL 机制）

Materialized Views（TimescaleDB/ClickHouse）
查询优化：分区表 + 索引 + 连续聚合（Continuous Aggregate）
回测专用：内存缓存 + VectorBT 向量化加速

7. 数据治理与安全

数据质量仪表盘：采集成功率、延迟、缺失率监控
备份策略：每日全备 + WAL 归档
权限控制：行级安全（RLS）+ 用户数据隔离
合规：敏感数据脱敏、操作审计、用户数据导出/删除权


实施优先级建议（分阶段上线）
Phase 1（已完成基础）：PostgreSQL + TimescaleDB + Redis + 多源采集
Phase 2（强烈建议下一步）：QuestDB/ClickHouse 引入 + UnifiedDataFacade 完善 + 数据质量监控
Phase 3：Vector Store + 完整 ETL Airflow 编排 + 数据版本管理

Cursor 开发建议：
如果你需要，我可以立即给你以下 Cursor Prompt：

数据模型完整定义（SQLAlchemy / Tortoise）
UnifiedDataFacade + Repository 实现
TimescaleDB + QuestDB 混合存储配置
多源采集器重构方案

请告诉我你想优先落地哪一部分，我马上给出详细的 Cursor Prompt + 代码框架。
例如回复：“给我 UnifiedDataFacade 的完整设计与 Prompt” 或 “先做数据模型”。
这个数据层设计完成后，你的 Quant Atlas 将具备高性能、可扩展、易维护的生产级数据能力，为后续 AI 多智能体和散户功能提供坚实支撑。