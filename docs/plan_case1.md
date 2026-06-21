 一、 核心架构问题 (Architectural Violations)

   1. 基础设施向应用层泄露 (Layering Violations)：
       * 现象：Application Service（如 StockApplicationService）中直接硬编码 SQL 和数据库连接逻辑，导致业务逻辑与存储实现紧耦合。
       * 后果：数据库改动或迁移将直接破坏业务服务，且无法在没有数据库实例的情况下对业务逻辑进行单元测试。
   2. 依赖反转（DIP）的原则性缺失：
       * 现象：应用层直接依赖基础设施的实体类（如 NewsArchiveRepository），而非定义好的抽象接口（Ports/Repository Interfaces）。
       * 后果：组件不可替换，测试时无法轻松注入 Mock。
   3. 职责分配混乱 (SRP/God Function)：
       * 现象：bootstrap_components/services.py 几乎承担了全系统所有服务的实例化职责，成为了一个无法维护的“God Function”。
   4. 接口与实现（Domain-Infrastructure）耦合：
       * 现象：基础设施（Infrastructure）中的持久化类（Repository）承担了数据种子化（Seeding）等非持久化职责。

  ---

  二、 重构建议 (Refactoring Recommendations)

  按 SOLID 原则，建议分阶段推进以下重构：

  1. 定义抽象层 (Dependency Inversion)
   * 动作：在 app/domain/interfaces（或 ports）下为所有基础设施资源定义接口，例如 IStockRepository。
   * 目的：确保应用层服务仅依赖于这些接口，而不关心具体是 MySQL、SQLite 还是 TDX 文件提供的数据。

  2. 清洗应用层 (Layer Cleanup)
   * 动作：
       * 将所有散落在 services 或 application 中的 SQL 迁移至 app/infrastructure/repositories。
       * 严禁在 Application Service 中出现 import sqlalchemy 或 pymysql 相关代码。
       * 通过 Repository 返回领域对象（Domain Entities），而不是直接返回数据库原始 Row 或 Dict。

  3. 异步解耦 (Decoupling Presentation from Infrastructure)
   * 动作：在 presentation/api 层，路由应只负责验证 Request 和调用 Application Service。
   * 模式建议：使用 Command/Query Bus（命令总线模式）。路由发送命令（Command），由总线路由到对应的 Handler。这可以切断 Presentation 对 Celery 等 Infrastructure 细节的直接访问。

  4. 引入依赖注入容器 (DI Container)
   * 动作：废弃 create_services 这种集中式实例化的写法。
   * 建议：改用 Python 的 dependency-injector 等库，实现基于声明式的构造函数注入。这能大幅降低 bootstrap 层的复杂性。

  5. 职责分离 (SRP)
   * 动作：将 Seeding/Bootstrap 相关逻辑从 Repository 的构造函数中剥离，移入独立的 app/bootstrap/lifecycle 处理程序。

  ---

  三、 优先级排序

   1. 高优先级（立刻行动）：
       * 提取 QlibPipelineService 和 StockApplicationService 中的 SQL，封装为 Repository 接口。
       * 解决 daily_sync 级别的冗余 SQL 调用。
   2. 中优先级（迭代改进）：
       * 重构 bootstrap_components，引入真正的 DI 容器，消除“God Function”。
       * 解耦 Presentation 层与 Celery 任务，统一采用总线模式路由。
   3. 低优先级（长期演进）：
       * 通过 Ports/Adapters 架构重构所有基础设施调用。

  这套重构路径能显著提高代码的可测性与健壮性，使其真正符合领域驱动设计（DDD）的要求。你需要我详细展开哪一个部分的重构指南吗？