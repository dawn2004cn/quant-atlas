“RD-Agent 生成因子 → Qlib 训练/回测 → TA 展示” 的闭环流程。
该方案以 RD-Agent (Q) 的 fin_factor（因子演化）或 fin_quant（因子+模型联合）模式为核心，RD-Agent 负责自动化研发（假设生成、代码实现），Qlib 负责可靠执行（数据、训练、回测、分析），TA 负责前端展示和决策注入。
1. 整体流程代码结构（推荐目录）
在您的 Flask + TradingAgents-CN 项目中新增以下结构（最小侵入）：
textproject/
├── rdagent_tasks.py          # Celery task：调用 RD-Agent 生成因子
├── qlib_service.py           # Qlib 训练、回测、信号提取
├── ta_integration.py         # 将 Qlib 结果推送到 TA（信号、报告、界面数据）
├── scripts/
│   ├── run_rdagent_factor.py # 独立运行 RD-Agent（测试用）
│   └── daily_quant_loop.py   # 每日自动化闭环
├── config/
│   ├── qlib_config.yaml      # Qlib workflow 配置
│   └── rdagent_config.yaml   # RD-Agent 参数
├── factor_library/           # RD-Agent 生成的因子保存目录（.py 或 .parquet）
└── app/routes/
    └── quant_api.py          # Flask API：/api/rdagent/run、/api/qlib/backtest、/api/signal/push
2. 核心实现代码
(1) RD-Agent 生成因子（研发自动化）
RD-Agent 提供现成 CLI：rdagent fin_factor（纯因子演化）或 rdagent fin_quant（因子+模型联合）。推荐先用 fin_factor（更快迭代）。
scripts/run_rdagent_factor.py（或 Celery task）：
Pythonimport os
from pathlib import Path
from rdagent.app.qlib_rd_loop.factor import main as fin_factor_main
# 或 from rdagent.app.qlib_rd_loop.quant import main as fin_quant_main

def run_rdagent_factor_generation(
    iterations: int = 5,           # 控制迭代次数，避免成本过高
    market: str = "csi300",
    benchmark: str = "SH000300",
    provider_uri: str = "~/.qlib/qlib_data/cn_data",
    output_dir: str = "./factor_library"
):
    os.environ.setdefault("QLIB_PROVIDER_URI", provider_uri)
    os.environ.setdefault("QLIB_MARKET", market)
    os.environ.setdefault("QLIB_BENCHMARK", benchmark)

    # 可自定义配置（覆盖模板中的 YAML）
    config = {
        "scenario": "rdagent.scenarios.qlib.experiment.quant_experiment.QlibQuantScenario",
        "iterations": iterations,
        "output_path": output_dir,
        # 可注入 TA 的前期分析作为背景知识
        "background": "结合近期市场情绪、宏观数据和通达信技术指标，挖掘低衰减的 A股 alpha 因子"
    }

    # 运行 RD-Agent（内部会调用 Co-STEER 生成代码 + Qlib 初步验证）
    fin_factor_main(**config)   # 或 fin_quant_main

    print(f"RD-Agent 完成 {iterations} 次迭代，新因子保存在 {output_dir}")
    return output_dir
Celery task 包装（推荐异步执行）：
Python# rdagent_tasks.py
from celery import shared_task
from .scripts.run_rdagent_factor import run_rdagent_factor_generation

@shared_task
def rdagent_factor_task(iterations=5, **kwargs):
    output_dir = run_rdagent_factor_generation(iterations, **kwargs)
    # 成功后触发下一步 Qlib 训练
    qlib_train_and_backtest.delay(factor_dir=output_dir)
    return {"status": "success", "factor_dir": output_dir}
(2) Qlib 训练 + 回测（可靠执行与验证）
RD-Agent 生成的因子通常以代码或 .parquet 形式输出（参考 combined_factors_df.parquet）。Qlib 用这些因子 + Alpha158 等构建 dataset，然后训练/回测。
qlib_service.py（关键函数）：
Pythonimport qlib
from qlib.constant import REG_CN
from qlib.workflow import R
from qlib.workflow.record_temp import SignalRecord, SigAnaRecord, PortAnaRecord
from qlib.utils import init_instance_by_config
import pandas as pd
from pathlib import Path

def init_qlib(provider_uri="~/.qlib/qlib_data/cn_data"):
    qlib.init(provider_uri=provider_uri, region=REG_CN)

def train_and_backtest_with_new_factors(
    factor_dir: str,
    model_type: str = "LGBModel",   # 或 "Transformer" 等
    workflow_config_path: str = "config/qlib_workflow.yaml"
):
    init_qlib()

    # 加载 RD-Agent 生成的新因子（假设输出为 parquet 或表达式）
    new_factors = pd.read_parquet(Path(factor_dir) / "combined_factors_df.parquet") if Path(factor_dir).exists() else None

    # 构建 workflow config（可动态生成）
    with open(workflow_config_path, "r") as f:
        config = yaml.safe_load(f)  # 使用 PyYAML

    # 如果有新因子，注入到 data_handler（示例：StaticDataLoader + Alpha158）
    if new_factors is not None:
        config["dataset"]["kwargs"]["handler"]["kwargs"]["static_data"] = new_factors

    # 运行完整 workflow（数据集构建 → 训练 → 回测 → 分析）
    with R.start(experiment_name="rdagent_new_factor"):
        dataset = init_instance_by_config(config["dataset"])
        model = init_instance_by_config(config["model"])   # LGBModel / LSTM 等

        model.fit(dataset)

        # 记录与分析
        recorder = R.get_recorder()
        sr = SignalRecord(model, dataset, recorder)
        sr.generate()

        sar = SigAnaRecord(recorder)
        sar.generate()

        par = PortAnaRecord(recorder, config.get("strategy", {"class": "TopkDropoutStrategy"}))
        par.generate()

        # 提取关键结果
        analysis = recorder.load_object("port_analysis")
        ic_ir = recorder.load_object("ic")

    results = {
        "ic": ic_ir.mean().get("IC", 0),
        "ir": ic_ir.mean().get("IR", 0),
        "annual_return": analysis["excess_return"].mean() * 252 if "excess_return" in analysis else 0,
        "sharpe": analysis.get("sharpe", 0),
        "signal_df": sr.load()   # 预测信号，用于选股
    }

    return results, recorder.get_artifact_uri()  # 返回信号和报告路径
示例 workflow_config.yaml（config/qlib_workflow.yaml，基于官方 LightGBM + Alpha158）：
YAMLdataset:
  class: DatasetH
  kwargs:
    handler:
      class: Alpha158Handler  # 或自定义加入新因子
      kwargs:
        start_time: "2008-01-01"
        end_time: "2020-08-01"
        fit_start_time: "2008-01-01"
        fit_end_time: "2014-12-31"
        # static_data: 新因子 parquet（动态注入）

model:
  class: LGBModel
  module_path: qlib.contrib.model.gbdt
  kwargs:
    loss: mse
    learning_rate: 0.05
    # ... 其他超参

strategy:
  class: TopkDropoutStrategy
  kwargs:
    topk: 50
    n_drop: 5
(3) TA 展示集成（信号与报告推送）
ta_integration.py：
Pythonfrom your_tradingagents.models import Strategy, Signal, BacktestReport  # 假设 TA 的模型

def push_to_tradingagents(qlib_results, factor_name="rdagent_new_factor"):
    # 1. 保存新策略/信号到 TA 数据库
    signal_df = qlib_results["signal_df"]  # 股票 + 预测分数
    for _, row in signal_df.iterrows():
        Signal.objects.create(
            stock=row["instrument"],
            score=row["score"],        # 或预测回报
            source="RD-Agent + Qlib",
            factor=factor_name,
            date=row["datetime"]
        )

    # 2. 创建回测报告
    report = BacktestReport.objects.create(
        name=f"RD-Agent Factor {factor_name}",
        annual_return=qlib_results["annual_return"],
        sharpe=qlib_results["sharpe"],
        ic=qlib_results["ic"],
        ir=qlib_results["ir"],
        raw_data=qlib_results  # 或报告路径
    )

    # 3. 通知 TA 界面刷新（WebSocket 或 API 调用）
    # 示例：调用 TA 的内部函数更新全景页、自选股、中长线选股
    update_dashboard_signals(report.id)

    # 4. 可选：让 TA 的多代理分析该新因子（增强决策）
    from tradingagents.agents import AnalystAgent
    AnalystAgent.analyze_new_factor(factor_name, qlib_results)

    return report.id
Flask API 示例（app/routes/quant_api.py）：
Pythonfrom flask import Blueprint, request, jsonify
from rdagent_tasks import rdagent_factor_task
from qlib_service import train_and_backtest_with_new_factors
from ta_integration import push_to_tradingagents

quant_bp = Blueprint("quant", __name__)

@quant_bp.route("/rdagent/run", methods=["POST"])
def run_rdagent():
    data = request.json
    task = rdagent_factor_task.delay(iterations=data.get("iterations", 5))
    return jsonify({"task_id": task.id, "status": "started"})

@quant_bp.route("/qlib/backtest", methods=["POST"])
def qlib_backtest():
    factor_dir = request.json.get("factor_dir")
    results, _ = train_and_backtest_with_new_factors(factor_dir)
    report_id = push_to_tradingagents(results)
    return jsonify({"results": results, "ta_report_id": report_id})
3. 每日自动化闭环（推荐）
scripts/daily_quant_loop.py（Celery 或 cron 调用）：
Pythondef daily_quant_pipeline():
    # 1. RD-Agent 生成/迭代因子
    factor_dir = run_rdagent_factor_generation(iterations=3)

    # 2. Qlib 训练 + 回测验证
    results, _ = train_and_backtest_with_new_factors(factor_dir)

    # 3. 推送到 TA 展示
    push_to_tradingagents(results)

    # 4. 可选：如果 IC/IR 达标，加入 TA 的 40+ 策略池
    if results["ir"] > 0.8:
        add_to_ta_strategy_pool(factor_dir)
4. 使用建议与注意事项

启动顺序：先确保 Qlib 数据已初始化（您的通达信 + AKShare 已打通），然后运行 RD-Agent（它会自动调用 Qlib 验证）。
控制成本：RD-Agent 迭代次数建议 3~8 次；使用本地 LLM（如 DeepSeek）或 LiteLLM 配置。
因子注入方式：RD-Agent 常输出表达式或 parquet，直接注入 Qlib 的 StaticDataLoader 或自定义 DataHandler。
与 TA 40+ 策略融合：新因子可作为额外特征，与原有策略 ensemble（加权信号）。
界面增强：在 TA 的“回测”“中长线选股”“全景页”中增加 “RD-Agent Alpha” tab，展示 IC 曲线、因子重要性（Qlib PortAnaRecord 输出）。
调试技巧：从小数据集（CSI300 子集）开始测试；查看 RD-Agent 日志（通常在 output 目录）。

这个闭环让 RD-Agent 自动产生新想法和代码，Qlib 严谨验证并生成信号，TA 负责用户可见的展示和决策，形成高效自动化量化工厂。
如果需要完整 YAML 配置模板、特定模型（LSTM/Transformer）的 workflow 示例、Celery + Redis 配置细节，或针对您现有代码的适配修改，请提供更多信息（如当前 RD-Agent 运行命令或 Qlib 数据路径），我可以给出更精确的代码片段！