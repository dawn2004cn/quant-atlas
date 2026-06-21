
已完成多agent协同审计：产品/功能、前端/UI、技术架构、安全/性能、重构路线图5个视角并行分析，并用代码证据校准。未修改代码。
总体判断
Quant-Atlas 是一个“功能广度很大、工程边界偏失控”的全栈量化研究平台。它不是缺功能，而是功能、服务、路由、前端页面扩张速度超过了架构约束。
主观评分：
维度	评分	判断
功能覆盖	8/10	行情、策略、AI、因子、Alpha、数据湖、交易风控、用户画像都有
功能闭环	5/10	多个功能停留在服务/路由/页面，缺少稳定数据闭环
架构清晰度	4/10	分层存在，但大量 Any、动态导入、全局 registry、宽泛异常破坏边界
前端体验	4/10	页面多，AJAX 错误处理、模板继承、CSS 设计系统不足
安全风险	3/10	存在高危命令注入、路径遍历、数据删除风险
工程治理	5/10	CI 已存在，但覆盖率门槛低，依赖源碎片化
已核实不是问题的项目
根据 docs/重构.md 和当前代码，以下旧风险不应再作为主线待办：
- 
CI 已存在：.github/workflows/ci.yml:10-67
- 
app/application/services/* 到 app/modules/* 的迁移已完成，旧路径是 shim
- 
.db 散落问题已做过清理和登记：docs/重构.md:102-127
- 
TDX IP 已配置化：docs/重构.md:19
- 
硬编码 AdminPassword123! / root123 已清除：docs/重构.md:20
- 
Docker / Alembic 已存在：docs/重构.md:24
- 
DataSourceRegistry、CapabilityRegistry 已存在：docs/重构.md:25-26
功能审计结论
1. 功能版图很完整
已实现的核心能力包括：
- 
行情数据接入与同步
- 
策略向导、策略模板、快速回测
- 
AI 研报、AI 投委会、RAG、语音简报
- 
因子工厂、因子演化、因子仓库
- 
Alpha Marketplace / 信誉市场
- 
数据湖、统一查询、遗留迁移
- 
预交易风控、ATR 仓位建议
- 
用户画像、心理服务、知识服务
- 
任务中心、事件总线、能力注册
证据：
- 
app/presentation/api/v1_context.py:28-136 暴露大量服务依赖
- 
app/presentation/api/routes_v1_strategy_wizard.py:6-7 接入策略向导服务
- 
app/presentation/api/routes_v1_alpha_marketplace.py:26-221 接入 Alpha Marketplace
- 
app/modules/execution/services/pre_trade_preflight_service.py:10-129 实现预交易 ATR 风控
- 
app/presentation/web/pages_ai.py:113-121 注册 Alpha Marketplace 和 Strategy Wizard 页面
2. 功能深度不均，部分链路未闭环
最明显的功能断裂：
问题
StrategyWizardService 双定义
Portfolio 模块注册了路由但 wire() 为空
预交易 ATR 计算异常时静默返回 0
Alpha Marketplace 前端页面存在，但服务仍局部实例化
大量可选服务通过 getattr(..., None) 注入
界面审计结论
当前模板规模：
- 
104 个 HTML 模板
- 
102 个 routes_v*.py API 路由模块
- 
1881 个 app/ Python 文件
- 
351 个测试文件
主要界面问题
问题	证据
模板继承不统一	strategy_wizard.html:1-7 是独立 HTML shell，引用 /static/css/main.css
全局 JS 一次性加载过重	base.html:262-273 每页加载 jQuery、api_client、markdown、focus、state_bus、chart 等
AJAX 错误处理弱	strategy_wizard.html:103-190 多处 fetch() 无 .catch()
导航信息架构过重	base.html:34-132 一级菜单承载大量二级功能
语言/国际化不一致	strategy_wizard.html:2 为 lang="en"，正文英文
CSS 设计系统未统一	strategy_wizard.html:7-30 独立定义按钮、卡片、指标样式
界面重构不应先做“大 UI 重写”。应先做基线：
1. 
统一模板继承
2. 
全局 fetch 错误兜底
3. 
提取 design tokens
4. 
删除重复模板
5. 
对核心页面做 Lighthouse 审计
技术架构审计结论
1. 分层存在，但边界被运行时动态性破坏
关键证据：
- 
ApiV1Context 平铺 100+ 服务字段：app/presentation/api/v1_context.py:28-136
- 
字段大量使用 Any：app/presentation/api/v1_context.py:28-136
- 
路由层仍通过 registry 动态取服务：app/presentation/api/routes_v1_strategy_wizard.py:21-27
- 
bootstrap.py 单点职责过重：app/bootstrap.py:48-343
- 
多处 import/初始化失败被吞掉：app/bootstrap.py:180-341
这说明当前架构不是“没有架构”，而是“架构被动态注册和 fallback 机制不断绕过”。
2. 注册体系复杂
当前存在：
- 
ServiceRegistry / TypedRegistry
- 
RouteRegistry
- 
ContextModule
- 
CapabilityRegistry
- 
DataSourceRegistry
- 
多个 wiring_*.py 工厂注册
这不是问题本身，问题是它们缺少统一契约和测试保护。重构方向不是再引入一个更大的 registry，而是：
- 
冻结现有 registry
- 
新增依赖必须有契约测试
- 
禁止继续新增隐式动态导入
- 
逐步把关键服务改为显式注入
3. 事件流不可审计
证据：
- 
本地 EventBus 将事件转成 dict：app/core/event_bus.py:325-377
- 
handler 异常只记录 error：app/core/event_bus.py:341-346
- 
WebSocket 广播失败只 debug：app/core/event_bus.py:404-417
- 
docs/重构.md:81-97 已确认跨进程事件序列化协议未统一
这对投研、交易、任务状态类应用很危险，因为事件是系统可观测性的主干。
安全与性能风险
P0 高危
风险	证据
命令注入：BackgroundRunTool	app/infrastructure/agent/swarm/tools/background_tools.py:25,41,89
命令注入：BashTool	app/infrastructure/agent/swarm/tools/bash_tool.py:44-49
路径遍历：uploads	app/presentation/static_files.py:37-40
MySQL TRUNCATE	app/infrastructure/repositories/mysql/mysql_tdx_dayk_repository.py:690-703
DDL RENAME 无锁	app/infrastructure/repositories/mysql/mysql_tdx_dayk_repository.py:736-790
P1 中高危
风险	证据
Flask secret key 空默认	app/config/settings.py:359
敏感凭证缓存	app/config/settings.py:618-651
EventBus 宽泛异常	app/core/event_bus.py:341-346,404-417
同步 requests 调用	多处 provider 使用同步 HTTP
SSE 无连接限制	任务流/工作流 SSE 路由
真实重构方案
原则：不要大重写。当前代码已经能跑、有 CI、有大量功能，最危险的是在未完成审计前做大规模重写。
P0：1-2 周，安全止血
必须优先做：
1. 
禁用或白名单化 BackgroundRunTool / BashTool
2. 
修复 /uploads/<path:filename> 路径遍历
3. 
TRUNCATE / RENAME 加管理锁、二次确认、操作审计
4. 
所有高危操作增加 request_id、操作者、参数快照
5. 
禁止新增 shell=True
验收：
grep -R "shell=True" app/infrastructure/agent/swarm/tools app/presentation
grep -R "TRUNCATE TABLE\|RENAME TABLE" app/infrastructure/repositories/mysql
目标：高危命令执行入口为 0，DDL 操作有锁和审计。
P1：2-4 周，测试护栏
当前覆盖率门槛只有 30%：
- 
pyproject.toml:44-49
- 
.github/workflows/ci.yml:46
docs/重构.md:38-78 已指出 T-1 测试覆盖不足。
优先补测：
1. 
trade_outcome_review_service
2. 
pre_trade_preflight_service
3. 
event_bus
4. 
alpha_marketplace_service
5. 
static_files
6. 
background_tools / bash_tool
验收：
python -m pytest tests/domain/test_market_regime_service.py tests/domain/test_pre_trade_preflight_service.py tests/core/test_circuit_breaker.py -q
本次已验证：49 passed。
P2：1-2 个月，架构收敛
不要推翻 registry，先收敛边界：
1. 
冻结 ApiV1Context，禁止继续新增平铺字段
2. 
新增服务必须通过契约测试
3. 
把 Any 服务字段逐步替换为 Protocol
4. 
禁止新增 __import__ 工厂
5. 
关键服务改为构造器注入
6. 
事件统一 schema：
- 
event_type
- 
event_id
- 
timestamp
- 
source
- 
payload
证据：
- 
docs/重构.md:81-97 已确认事件序列化协议未统一
- 
app/core/event_bus.py:325-377 当前仍是 dict 化事件
验收：
grep -c "except Exception" app/core/event_bus.py
pytest tests/test_event_serialization.py -q
P3：2-3 个月，前端工程化
前端不要直接重写所有页面。先做基线：
1. 
输出 docs/frontend_baseline.md
2. 
统计重复 CSS/JS
3. 
修复独立 shell 页面
4. 
统一全局 fetch 错误处理
5. 
建立 design tokens
6. 
核心页面 Lighthouse 目标：
- 
Performance ≥ 90
- 
Best Practices ≥ 90
- 
768px 以下无水平滚动
证据：
- 
docs/重构.md:130-149
- 
strategy_wizard.html:1-7
- 
base.html:262-273
P4：依赖与发布治理
当前依赖源碎片化：
- 
requirements.txt
- 
requirements-compute.txt
- 
requirements-qlib.txt
- 
pyproject.toml
- 
package-lock.json
- 
bun.lock
docs/重构.md:208-225 已列为 T-8。
建议：
1. 
Python 以 pyproject.toml 为单一事实源
2. 
requirements 降为派生文件
3. 
前端 npm / bun 二选一
4. 
CI 增加：
- 
pip-audit
- 
npm audit 或对应 bun audit
- 
覆盖率提升到 50%
90 天路线图
时间	目标	产出
W1-W2	安全止血	命令执行入口清零、uploads 修复、DDL 加锁
W2-W4	测试护栏	关键服务单测、覆盖率从 30% 提升到 50%
W4-W6	事件协议	统一事件 schema、序列化测试、异常日志
W6-W8	依赖治理	单一依赖源、audit 门禁、lockfile 清理
W8-W10	前端基线	frontend baseline、重复样式清单、tokens 草案
W10-W12	架构收敛	ApiV1Context 冻结、Protocol 契约、禁止新动态导入
最小可行第一步
先做这三件事：
1. 
修掉 P0 安全入口：BackgroundRunTool、BashTool、/uploads
2. 
补 trade_outcome_review_service、event_bus、static_files 测试
3. 
输出 frontend_baseline.md，不要先重写 UI
本次验证
已执行：
python -m compileall -q app
python -m pytest tests/domain/test_market_regime_service.py tests/domain/test_pre_trade_preflight_service.py tests/core/test_circuit_breaker.py -q
结果：
- 
compileall 通过
- 
关键服务测试：49 passed
统计结果：
- 
app/ Python 文件：1881
- 
测试文件：351
- 
HTML 模板：104
- 
API 路由模块：102
- 
CI workflow：2
本地尝试启动 Flask app 做 boot smoke 时在 120s 超时，因此启动稳定性未作为本次已验证项；但 CI 中已有 boot-smoke job：.github/workflows/ci.yml:48-67。