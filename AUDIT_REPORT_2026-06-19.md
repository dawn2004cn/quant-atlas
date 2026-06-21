# Quant Atlas 全方位代码审计报告

**审计日期**: 2026-06-19
**审计范围**: 2132 Python 文件, 191 包, 112 模板, 436 测试文件, 55+ 策略模型
**审计智能体**: 代码库导航、安全工程师、软件架构师、前端开发者、量化分析、测试审计、性能审计、幕僚长综合
**总发现数**: 60+ 项（按严重程度分级）

---

## 一、执行摘要 (CEO Perspective)

### 核心判断

Quant Atlas 是一个**架构野心极大但执行粗糙**的系统。它声称采用四层 DDD 架构，但实际上存在严重的架构漂移——`app/modules/` 下有 22 个功能模块直接跨越了表现层、应用层和基础设施层的边界。

**技术债务比率**：约 35-40% 的代码库在修补已知问题，而非交付新功能。

### 业务价值 vs 技术债务

| 维度 | 评分 (1-10) | 说明 |
|------|-------------|------|
| 架构设计 | 6 | 四层 DDD 理念正确，但 `modules/` 打破了分层 |
| 安全基础 | 2 | 凭证明文提交到 Git，3 个数据库均有 SQL 注入 |
| 量化引擎 | 5 | 回测引擎正确但策略缺乏交易成本和过拟合防护 |
| 前端体验 | 4 | Vue 3 SPA + 112 个 Jinja2 模板，三者割裂 |
| 测试质量 | 3 | 436 测试文件但 ~55 个只有 print() 无断言 |
| 性能表现 | 4 | N+1 查询、无界内存缓存、缺失复合索引 |

### 不改的风险

1. **数据泄露**：`.env` 含 11 个明文密钥（含 ClickHouse 密码 `qwerty`）
2. **数据库被破坏**：3 个数据库后端均存在 SQL 注入
3. **量化结果不可信**：策略无交易成本建模，回测胜率虚高 5-15%
4. **用户信任崩塌**：作为投研平台，安全性差会直接摧毁品牌

---

## 二、关键发现（必须立即修复）

### 🔴 CRITICAL

| # | 发现 | 文件 | 修复工时 |
|---|------|------|----------|
| C1 | `.env` 含 11 个明文密钥提交到 Git | 仓库根目录 `.env` | 2 小时 |
| C2 | ClickHouse SQL 注入 — `_sql_escape()` 被绕过 | `clickhouse_ohlcv_sync_service.py:41-43` | 4 小时 |
| C3 | QuestDB SQL 注入 — `_escape_literal()` 相同问题 | `questdb_ohlcv_writer.py:188,193` | 4 小时 |
| C4 | 策略模型无交易成本建模，回测虚高 5-15% | 全部 8 个策略文件 (~3600 行) | 1 天 |
| C5 | 内存缓存无上限，持续负载下可能消耗 GB 级内存 | `memory_cache.py:31-50` | 1 小时 |

### 🟠 HIGH

| # | 发现 | 文件 | 修复工时 |
|---|------|------|----------|
| H1 | 模板 `| safe` 过滤器导致存储型 XSS | `macros.html:52` | 30 分钟 |
| H2 | 用户数据导出/删除存在 IDOR | `routes_v1_user_lifecycle.py:51-75` | 30 分钟 |
| H3 | 登录时未重置 Session ID（会话固定攻击） | `auth.py:80-83` | 30 分钟 |
| H4 | AI 生成的回测脚本通过 `subprocess.run()` 执行 | `process_runner.py:103,170` | 1 天 |
| H5 | `git checkout` 命令注入（用户提供的 revision 字符串） | `code_checkout.py:44` | 1 小时 |
| H6 | `serialize()` 函数盲 dump `__dict__` 泄露敏感字段 | `responses.py:22-34` | 4 小时 |
| H7 | 文件上传仅校验扩展名，无魔数验证 | `moments_service.py:179-229` | 3 小时 |
| H8 | 回测引擎信号权重归一化丢失信号强度信息 | `base.py:112-113` | 2 小时 |
| H9 | 缺失复合索引导致百万级表全表扫描 | `market.py`, `advanced.py` | 4 小时 |
| H10 | Vue 3 SPA 中 `BacktestResult` 类型为 `Record<string, unknown>` | `backtest.ts:38` | 2 小时 |
| H11 | Agent 研究管线缺乏幻觉防护（仅 prompt 级别） | `nodes/__init__.py` | 1 天 |
| H12 | 55+ 测试文件只有 `print()` 无断言，无法失败 | 遍布 tests/ | 重构 |

---

## 三、高优先级（接下来 2 个 Sprint）

### 1. RBAC 全面实施
**现状**：几乎所有 API 端点仅有 `@login_required`，无角色检查
**影响**：任何认证用户可访问投资委员会评估、回测执行、账户删除等管理功能
**修复**：创建 `@require_role()` 装饰器，应用到 ~15 个管理端点
**工时**：8 小时

### 2. 三层数据库参数化查询统一
**现状**：`_sql_escape()` 和 `_escape_literal()` 在 3+ 模块中重复
**修复**：统一到 `infrastructure/database/sql_safety.py`，为每个适配器提供参数化查询构建器
**工时**：12 小时

### 3. 策略交易成本建模
**现状**：40+ 策略不扣除佣金、印花税、滑点
**修复**：为 `BaseTradingStrategy` 添加 `transaction_cost_bps` 参数
**工时**：2 天

### 4. 前端三套样式系统合并
**现状**：三个竞争的 CSS 设计系统 + 大量内联样式 + 模板内 `<style>` 块
**修复**：统一到 Tailwind CSS + CSS 自定义属性
**工时**：3 天

### 5. 测试质量提升
**现状**：平均每个测试 2.6 个断言，55+ 文件只有 print()
**修复**：移除无断言测试，为关键路径添加行为测试
**工时**：2 天

---

## 四、中优先级（下个季度）

| 项目 | 详情 | 预估工时 |
|------|------|----------|
| v1 到 v2 API 迁移 | V2 仅覆盖 ~25 端点 vs V1 的 ~100+ | 2 周 |
| 缓存失效机制 | Redis 缓存无显式失效，依赖 TTL 过期 | 3 天 |
| 依赖版本锁定 | `requirements.txt` 全部使用 `>=` | 1 天 |
| 数据加载器批量优化 | Tushare 逐个符号请求，无速率限制感知 | 2 天 |
| 前端 ESLint + TypeScript 严格模式 | 无 lint 配置，`Record<string, unknown>` 泛滥 | 2 天 |
| 量化因子 IC 监控 | 已有但无自动化预警 | 1 天 |

---

## 五、低优先级（Backlog）

- 文件上传大小限制
- CSP `unsafe-inline` 迁移到 nonce
- 命令安全检查中的反引号绕过
- 错误日志中的 PII 脱敏
- 缺失的 COOP/COEP 安全头
- API 错误详情泄露（DEBUG 模式保护）

---

## 六、重构优先级矩阵 (Impact × Effort)

```
                    低努力         中努力          高努力
              +------------+------------+------------+
高影响   C1    | C2         | H1-RBAC    | C4-交易成本|
         | C3-SQL注入    | H6-序列化  | H4-子进程 |
         | H2-IDOR      | H7-上传验证 | H11-幻觉防护|
              +------------+------------+------------+
中影响   C5-内存缓存| H8-信号权重  | H9-索引优化 | H10-Vue类型|
         | H3-Session | 策略成本参数 | 数据加载优化|
              +------------+------------+------------+
低影响   上传大小    | CSP nonce   | 因子IC监控  |
         | 错误日志脱敏| 前端ESLint  | 依赖锁定    |
              +------------+------------+------------+
```

---

## 七、90 天分阶段迁移计划

### 第 1 周：紧急安全修复（停止所有功能开发）

| 任务 | 负责人 | 工时 |
|------|--------|------|
| 旋转所有 11 个密钥 | DevOps | 2h |
| `.env` 加入 `.gitignore` + BFG 清理历史 | DevOps | 1h |
| 移除 `macros.html:52` 的 `| safe` | Web | 30min |
| 添加 `routes_v1_user_lifecycle.py` 所有权校验 | Backend | 30min |
| 登录时 `flask.session.regenerate()` | Web | 30min |
| `bootstrap.py` 强制 `app.debug = False` | Backend | 30min |
| 内存缓存替换为 TTLCache | Backend | 1h |

**里程碑**：零 CRITICAL/HIGH 安全问题

### 第 2-3 周：注入修复

| 任务 | 负责人 | 工时 |
|------|--------|------|
| ClickHouse 同步：参数化查询 | Data Eng | 4h |
| QuestDB 写入器：切换到 ILP 协议 | Data Eng | 4h |
| MySQL TDX 仓库：统一 `safe_sql_identifier()` | Data Eng | 4h |
| 代码检出：revision 正则验证 | Backend | 1h |
| 命令安全：反引号加入黑名单 | Backend | 1h |

**里程碑**：所有 SQL/命令注入修复，自动化注入测试覆盖

### 第 4-5 周：访问控制加固

| 任务 | 负责人 | 工时 |
|------|--------|------|
| 创建 `@require_role()` 装饰器 | Backend | 2h |
| 应用到 ~15 个管理端点 | Backend | 4h |
| 替换 `serialize()` 为显式 DTO | Backend | 4h |
| 添加 `python-magic` 上传验证 | Backend | 3h |
| 密码哈希迁移流程 | Backend | 4h |
| 回测子进程容器化 | Infra | 8h |

**里程碑**：无认证用户无法访问管理功能，敏感数据不泄露

### 第 6-7 周：防御纵深 + 量化修正

| 任务 | 负责人 | 工时 |
|------|--------|------|
| JWT 路由 CSRF 保护 | Backend | 6h |
| 复合密钥速率限制 | Backend | 2h |
| 策略交易成本参数化 | Quant Eng | 2d |
| 策略过拟合检测框架 | Quant Eng | 3d |
| 依赖锁定 + pip-audit CI | DevOps | 4h |
| 测试质量提升（移除 print-only 测试） | QA | 2d |

**里程碑**：回测结果反映真实交易成本，CI 自动检测注入

### 第 8-9 周：架构对齐

| 任务 | 负责人 | 工时 |
|------|--------|------|
| 层合规审计（domain 不依赖 infrastructure） | Architect | 1d |
| v2 API 迁移路线图 | Backend | 2d |
| 前端三套 CSS 合并 | Frontend | 3d |
| Vue 3 类型安全改造 | Frontend | 2d |
| 复合索引添加 | Data Eng | 1d |
| 缓存失效事件机制 | Backend | 2d |

**里程碑**：四层架构合规，前端统一设计系统

### 第 10-12 周：收尾 + 量化增强

| 任务 | 负责人 | 工时 |
|------|--------|------|
| Agent 幻觉防护（程序级引用验证） | AI Eng | 3d |
| 数据加载器批量优化 | Data Eng | 2d |
| 前端无障碍改进 | Frontend | 2d |
| 安全审计自动化（Bandit + OWASP ZAP） | DevOps | 1d |
| 文档更新 + 开发者指南 | Tech Writer | 2d |

**里程碑**：生产就绪，SOC 2 Type II 基线

---

## 八、各领域详细发现摘要

### 8.1 量化分析领域

**策略偏差**：
- 全部 40+ 策略无交易成本建模（佣金 + 印花税 + 滑点）
- 高频均值回归策略（如 `ConnorsRSI2Strategy`）实际收益被高估 5-15%
- 卖出信号与买入信号在同一 K 线可触发，导致持仓时间为 0 的虚假交易
- 幸存者偏差：数据加载器不包含退市股票

**技术指标验证**：
- RSI（Wilders 平滑）✅ 正确
- MACD（EMA 12/26/9）✅ 正确
- 布林带（SMA 20 ± 2σ）✅ 正确
- ATR（Wilder 平滑）✅ 正确
- KDJ（ta 库标准随机振荡器）⚠️ 与通达信约定有 5-15% 差异
- SuperTrend（Chandelier Exit 近似）❌ 非真实 SuperTrend

**回测引擎**：
- T+1 规则 ✅ 正确
- 印花税历史版本 ✅ 正确（0.1% → 0.05% → 0.025%）
- 信号下一根 K 线执行 ✅ 正确
- 资金利用率归一化 ❌ 丢失信号强度信息
- 空闲现金无利息 ⚠️ 低估长期回测收益

### 8.2 前端领域

**三重设计系统冲突**：
1. Tailwind CSS（Vue SPA）
2. 内联样式 + `<style>` 块（Jinja2 模板）
3. 独立的 CSS 文件（`common.css`, `zen-finance.css`, `design-tokens.css`）

**模板质量问题**：
- `stock_detail.html` 428-519 行内联样式
- `index.html` 含 ~160 行内嵌 CSS
- 仅 3 个 Jinja2 宏复用，80+ 模板重复相同结构
- Alpine.js 与 Jinja2 混用增加调试复杂度

**Vue 3 SPA**：
- `BacktestResult` 类型为 `Record<string, unknown>` — 完全失去 TypeScript 意义
- 无 ESLint 配置
- SWR hooks 缺少错误重试计数配置

### 8.3 测试领域

**436 测试文件 / ~1241 测试函数 / ~3292 断言**：
- 平均每测试仅 2.6 个断言（偏低）
- 55+ 文件含 `print()` 无断言 — 不可能失败的测试
- CI 配置 `--cov-fail-under=50` 但实际运行排除慢测试，真实覆盖率估计 20-30%
- 最佳示例：`test_sanitize_ohlc_bar_repairs_envelope` — 测试 OHLC 无效包裹修复

### 8.4 性能领域

**N+1 查询**：
- `upsert_pool`：2000+ 股票逐行 SELECT → 10-40 秒延迟
- `IndicatorReconstructor`：批量回退时逐符号查询

**缓存问题**：
- 内存缓存无上限（纯 dict）
- Redis 缓存无显式失效机制
- `get_or_set` 存在缓存击穿竞态

**数据库**：
- `Stock.amount` 列错误索引
- 大表缺失复合索引（`archived_news`, `signal_flag_pool`, `ft_trades`, `kronos_predictions`）
- `/markets/<market>/quotes` 默认返回 6000 条无分页

---

## 九、成功指标

| 指标 | 当前值 | 目标值 | 期限 |
|------|--------|--------|------|
| CRITICAL/HIGH 安全问题 | 17 项 | 0 | Week 5 |
| 策略交易成本建模 | 0% | 100% | Week 7 |
| SQL 参数化覆盖率 | ~30% | 100% | Week 3 |
| 测试断言覆盖率 | 2.6/测试 | 5+/测试 | Week 7 |
| print-only 测试文件 | 55+ | 0 | Week 7 |
| 前端 CSS 系统 | 3 套 | 1 套 | Week 9 |
| 依赖锁定 | 0% | 100% | Week 7 |
| 内存缓存上限 | 无 | TTLCache | Week 1 |

---

## 十、资源需求

| 角色 | 人数 | 周期 | 主要职责 |
|------|------|------|----------|
| 后端工程师 | 1 | 12 周 | 安全修复、RBAC、注入修复、缓存 |
| DevOps/基础设施 | 1 | 4 周 | 密钥轮换、CI/CD、容器化 |
| 数据工程师 | 1 | 3 周 | SQL 参数化、索引优化、数据加载器 |
| 前端工程师 | 1 | 4 周 | CSS 合并、Vue 类型安全、无障碍 |
| 量化工程师 | 1 | 3 周 | 交易成本建模、过拟合防护 |
| QA 工程师 | 1 | 4 周 | 测试质量提升、安全回归测试 |

**总计**：约 6 人周 × 2 人 = **12 人周**（6 人 × 2 周并行）

---

*本报告由 7 个专业智能体协同审计 + 幕僚长综合生成*
*审计日期：2026-06-19*
*总分析 token 消耗：~575K*
