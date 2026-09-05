from __future__ import annotations

"""上游项目 → Quant Atlas 映射目录（领域层纯数据，无 Web 依赖）。

用于在 UI/文档中统一说明「集成落点」与面向对象六项原则的对应关系：
- **SRP**：每个上游能力对应 Atlas 内单一模块边界（适配器/服务/页面入口）。
- **OCP**：新增集成通过新增适配器与注册表条目扩展，避免修改核心调度。
- **LSP**：对外暴露的 Port（见 ``domain/ports.py``）实现可替换。
- **ISP**：按「数据 / 执行 / 分析 / Agent / 支付」拆分接口，调用方只依赖所需 Port。
- **DIP**：应用层依赖 Port 与领域实体；基础设施实现可替换（MySQL/CCXT/OpenBB 等）。
- **LoD**：页面只链接到稳定的应用服务入口，不暴露仓库细节。
"""


from dataclasses import dataclass
from typing import Literal

IntegrationLayer = Literal["data", "execution", "analytics", "agents", "payments", "ops"]


@dataclass(frozen=True)
class IntegrationRouteRef:
    """导航入口：抽象 ID（由表现层映射为具体 URL 或 Endpoint）。"""

    label: str
    nav_id: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class IntegrationCard:
    """一张「集成卡片」：对应一个上游项目在本仓库中的核心落点。"""

    key: str
    layer: IntegrationLayer
    source_project: str
    title: str
    summary: str
    solid_note: str
    code_paths: tuple[str, ...]
    routes: tuple[IntegrationRouteRef, ...]


def all_integration_cards() -> tuple[IntegrationCard, ...]:
    """静态目录：按当前代码结构维护（审计友好）。"""
    return (
        IntegrationCard(
            key="tradingagents_ai_hedge",
            layer="agents",
            source_project="TradingAgents-CN / ai-hedge-fund",
            title="多智能体研究与辩论链",
            summary="LangGraph 六分析师 + Supervisor + 牛熊/风险辩论；Gemini 等模型经统一 LLM 配置接入。",
            solid_note="DIP：研究编排依赖抽象工具与状态机，而非外部包直接耦合。",
            code_paths=(
                "app/agents/research/",
                "app/agents/research/graph.py",
                "app/application/services/ai_research_service.py",
            ),
            routes=(
                IntegrationRouteRef("AI 分析", nav_id="ai_analysis"),
                IntegrationRouteRef("研究闭环", nav_id="research_pipeline"),
                IntegrationRouteRef("AI 研究报告", nav_id="ai_research_report"),
            ),
        ),
        IntegrationCard(
            key="daily_stock_analysis",
            layer="analytics",
            source_project="daily_stock_analysis",
            title="每日复盘与研判模板",
            summary="Dashboard 合成提示、验证与导入等能力分散落在服务层，与研究流水线衔接。",
            solid_note="SRP：复盘提示（dashboard_prompt）与行情事实（Market/News）分离。",
            code_paths=(
                "app/agents/research/dashboard_prompt.py",
                "app/services/daily_analysis_service.py",
                "app/services/validation/prediction_validator.py",
            ),
            routes=(
                IntegrationRouteRef("研究闭环", nav_id="research_pipeline"),
                IntegrationRouteRef("AI 研究报告", nav_id="ai_research_report"),
            ),
        ),
        IntegrationCard(
            key="fingpt",
            layer="analytics",
            source_project="FinGPT",
            title="FinGPT 风格预测与舆情落地",
            summary="图节点 + 适配器落库（预测/情感），与研究报告段落对齐。",
            solid_note="ISP：情感/预测能力通过专用适配器接入；应用层写入与栈探测统一经 FinGPTApplicationService，持久化契约为 FinGPTPersistencePort（domain/ports.py）。",
            code_paths=(
                "app/agents/research/graph.py",
                "app/agents/research/fingpt_forecaster.py",
                "app/application/services/sentiment_fingpt_payload.py",
                "app/application/services/fingpt_application_service.py",
                "app/infrastructure/adapters/fingpt_adapter.py",
                "app/domain/ports.py",
            ),
            routes=(
                IntegrationRouteRef("AI 分析", nav_id="ai_analysis"),
            ),
        ),
        IntegrationCard(
            key="stock_analysis_tdx",
            layer="data",
            source_project="stock-analysis（通达信离线）",
            title="本机通达信数据层",
            summary="与通达信 PC 对等：HQ 批量实时行情 + 本地 vipdoc/lday 历史，缺失则 HQ 下载日线。",
            solid_note="OCP：新增本地读取器不改 MarketProvider 核心，仅扩展适配层。",
            code_paths=(
                "app/infrastructure/tdx_local/",
                "app/application/services/basic_market_data_service.py",
            ),
            routes=(
                IntegrationRouteRef("热点板块", nav_id="hot_sectors"),
                IntegrationRouteRef("个股详情", path="/stock/sh600519"),
            ),
        ),
        IntegrationCard(
            key="freqtrade",
            layer="execution",
            source_project="Freqtrade",
            title="交易生命周期（Bot）",
            summary="移植 Freqtrade 语义的状态机与持久化表结构，经 TradingBotService 编排。",
            solid_note="DIP：策略/交易所依赖端口注入，便于替换实盘网关。",
            code_paths=(
                "app/application/services/trading_bot_service.py",
                "app/domain/trading_entities.py",
                "app/infrastructure/database/mysql_client.py",
            ),
            routes=(
                IntegrationRouteRef("策略回测（对照）", nav_id="backtest"),
                IntegrationRouteRef("量化实验室", nav_id="quant_lab"),
            ),
        ),
        IntegrationCard(
            key="hyperswitch",
            layer="payments",
            source_project="Hyperswitch",
            title="支付编排（可选）",
            summary="PaymentIntent / Refund 编排与网关路由表；默认可接 Mock。",
            solid_note="SRP：编排引擎与具体网关适配器分离。",
            code_paths=(
                "app/application/services/payment_orchestrator.py",
                "app/infrastructure/adapters/payment_gateways/",
            ),
            routes=(
                IntegrationRouteRef("个人中心（账户相关入口）", nav_id="profile"),
            ),
        ),
        IntegrationCard(
            key="kronos",
            layer="analytics",
            source_project="Kronos",
            title="生成式 K 线预测（基础模型）",
            summary="KronosPredictorPort + 预测落库；可与实验室/回测对照使用。",
            solid_note="LSP：预测端口多种实现（本地权重/远程）可替换。",
            code_paths=(
                "app/infrastructure/adapters/kronos_adapter.py",
                "app/application/services/kronos_service.py",
            ),
            routes=(IntegrationRouteRef("量化实验室", nav_id="quant_lab"),),
        ),
        IntegrationCard(
            key="openbb",
            layer="data",
            source_project="OpenBB",
            title="全球多源行情编排",
            summary="OpenBBDataProvider + TTL 缓存表，扩展海外资产覆盖。",
            solid_note="LoD：上层只依赖 GlobalMarketService，不直连供应商 SDK。",
            code_paths=(
                "app/infrastructure/adapters/openbb_adapter.py",
                "app/application/services/global_market_service.py",
            ),
            routes=(IntegrationRouteRef("市场全景", nav_id="market_panorama"),),
        ),
        IntegrationCard(
            key="quantml",
            layer="analytics",
            source_project="QuantML",
            title="因子动物园（Factor Zoo）",
            summary="因子元数据同步与检索，服务量化实验与 RD-Agent 生态。",
            solid_note="DIP：因子读写经 QuantMLFactorRepository 端口。",
            code_paths=(
                "app/application/services/quantml_factor_service.py",
                "app/infrastructure/repositories/mysql_quantml_repository.py",
            ),
            routes=(IntegrationRouteRef("量化实验室", nav_id="quant_lab"),),
        ),
        IntegrationCard(
            key="quantml_agent",
            layer="agents",
            source_project="quantml-agent",
            title="大盘级 Agent 洞察",
            summary="AgenticAnalysisService：市场洞察与研报解读落库。",
            solid_note="ISP：与个股多智能体链路分离，避免 Agent 接口臃肿。",
            code_paths=(
                "app/application/services/agentic_analysis_service.py",
                "app/domain/agent_entities.py",
            ),
            routes=(
                IntegrationRouteRef("AI 分析", nav_id="ai_analysis"),
                IntegrationRouteRef("研报中心", nav_id="yanbao_hub"),
            ),
        ),
        IntegrationCard(
            key="gemini_llm",
            layer="ops",
            source_project="Gemini（统一 LLM 配置）",
            title="模型提供方编排",
            summary="用户在侧栏/配置中选择 Gemini 等提供商；RD-Agent 与 Agent 共用一套运行时配置策略。",
            solid_note="OCP：新增模型提供商通过配置表扩展，无需改核心业务。",
            code_paths=(
                "app/application/services/llm_user_config.py",
                "app/core/llm_config.py",
            ),
            routes=(
                IntegrationRouteRef("个人中心", nav_id="profile"),
                IntegrationRouteRef("量化实验室", nav_id="quant_lab"),
            ),
        ),
    )


def cards_by_layer() -> dict[IntegrationLayer, list[IntegrationCard]]:
    out: dict[IntegrationLayer, list[IntegrationCard]] = {
        "data": [],
        "execution": [],
        "analytics": [],
        "agents": [],
        "payments": [],
        "ops": [],
    }
    for c in all_integration_cards():
        out[c.layer].append(c)
    return out


LAYER_LABELS: dict[IntegrationLayer, str] = {
    "data": "数据平面（行情 / 缓存 / 本地通达信）",
    "execution": "执行平面（交易机器人 / 订单生命周期）",
    "analytics": "分析与预测（因子 / Kronos / FinGPT）",
    "agents": "智能体（多角色研究 / 大盘洞察）",
    "payments": "支付与商业化（Hyperswitch）",
    "ops": "运行时与模型运维（Gemini / RD-Agent / LLM）",
}
