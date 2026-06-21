3\. 分阶段实施路线图（贴合现状）

Phase 1: 数据统一与 Qlib 基础集成（最优先，1-2周）



安装：pip install qlib rd-agent akshare celery redis

TDX 数据导出：用工具或脚本将通达信日K导出为 CSV（字段：symbol, date, open, close, high, low, volume, amount 等）。

转换到 Qlib 格式：

用 Qlib 官方 scripts/dump\_bin.py（支持 CSV → .bin）。

或写简单脚本批量处理。



初始化 Qlib：在 Flask app startup 中 qlib.init(provider\_uri='\~/.qlib/qlib\_data/cn\_data', market='all')

新增 Flask API：

GET /data/status → 返回 Qlib 数据覆盖范围、最新日期。

POST /data/update → 触发 AKShare + TDX 增量更新 → dump\_bin。





Phase 2: RD-Agent 自动因子生成 + 验证



配置 RD-Agent(Q) 使用现有 Qlib 数据（参考官方 factor\_template）。

写一个 Celery task：run\_rdagent\_factor\_loop() → 生成新因子 → 保存到因子库 → Qlib backtest 验证（IC/IR/收益）。

Flask API：POST /rdagent/factor → 触发任务，返回报告（假设、代码、验证指标）。

界面增强：在“回测”或新增“AI研究”页显示 RD-Agent 日志和 Top 因子。



Phase 3: 模型训练 + 增强回测/选股



用 Qlib Workflow 训练 LightGBM / LSTM 等（可 ensemble 已有策略信号）。

预测信号注入现有选股模块（中长线选股用 Transformer 长期预测）。

回测模块：新增 Qlib Backtest 选项，与原有并行对比。

监控：新增仪表盘显示因子衰减、模型漂移、IC 热力图（用 Plotly）。



持续优化：



三级缓存适配 Qlib Dataset。

40+ 策略中选 5-10 个用 Qlib 重新实现/回测，提升一致性。

警报：IC < 阈值 或 回撤超标时推送。

