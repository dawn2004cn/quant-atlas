"""Node implementations for the custom trading research graph.

Each node is a self-contained async function that transforms ResearchState
into a partial result dict.  The graph builder (graph.py) wires these
nodes together with edges and conditional routers.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logger import get_logger
from app.tools.quant_tools import (
    get_cn_financial_statements,
    get_cn_longhu_for_symbol,
    get_cn_research_reports,
    get_kline_chart,
    get_market_data,
    get_qlib_factor_snapshot,
    get_research_pipeline_status,
    get_stock_news,
    get_tdx_local_snapshot,
    get_user_watchlist,
    get_yanbao_market_digest,
    probe_ticker,
    run_backtest,
    run_qlib_unified_backtest,
    stock_selector,
)

from ..react_loop import react_with_tools
from ..state import INVESTMENT_DEBATE_ROUNDS, RISK_DEBATE_ROUNDS, ResearchState

logger = get_logger(__name__)


# ── Toolsets ───────────────────────────────────────────────────────────

TOOLS_COMMON = [
    get_market_data,
    get_kline_chart,
    stock_selector,
    probe_ticker,
    get_research_pipeline_status,
    get_tdx_local_snapshot,
]

TOOLS_TECHNICAL = [
    get_market_data,
    get_kline_chart,
    stock_selector,
    probe_ticker,
    get_cn_longhu_for_symbol,
    get_qlib_factor_snapshot,
]

TOOLS_FUNDAMENTAL = [
    get_market_data,
    get_kline_chart,
    get_qlib_factor_snapshot,
    stock_selector,
    probe_ticker,
    get_cn_financial_statements,
    get_cn_research_reports,
    get_yanbao_market_digest,
]

TOOLS_BACKTEST = [
    get_market_data,
    get_kline_chart,
    get_qlib_factor_snapshot,
    run_backtest,
    run_qlib_unified_backtest,
    get_tdx_local_snapshot,
    stock_selector,
    get_user_watchlist,
]

TOOLS_SENTIMENT = [
    stock_selector,
    get_market_data,
    get_user_watchlist,
    get_stock_news,
    get_yanbao_market_digest,
]


def _suffix() -> str:
    from app.tools.quant_tools import quant_tools_agent_system_suffix
    return quant_tools_agent_system_suffix()


# ── Supervisor ─────────────────────────────────────────────────────────

async def supervisor_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    sys = f"""你是 **Supervisor Orchestrator**（研究编排者）。
你的任务：阅读用户问题与标的，输出简洁的「研究计划」：各分析师应关注的重点、数据缺口假设、与辩论阶段需对齐的结论类型。
不要编造行情数字；编排须严格落在「支持市场」内；无工具调用权限时不得捏造 OHLC/回测指标。
若需了解平台 **Qlib→RD→门禁→Agent** 链路健康度，可调用 get_research_pipeline_status；前端同路径见「研究闭环」页。
{_suffix()}
"""
    log = state.get("conversation_log") or []
    log_txt = "\n".join(log[-30:]) if log else "(首轮，无历史)"
    user = (
        f"ticker={state.get('ticker')}\nuser_id={state.get('user_id')}\nquery={state.get('query')}\n"
        f"---\n本轮前对话摘要（仅用户/系统写入的 query 时间线）:\n{log_txt}"
    )
    memo = await react_with_tools(llm, [], system=sys, user=user, max_rounds=1)
    return {
        "supervisor_memo": memo,
        "debate_turn": 0,
        "risk_debate_turn": 0,
        "investment_debate_state": {"bull_history": "", "bear_history": "", "history": ""},
        "risk_debate_state": {"risky_history": "", "safe_history": "", "history": ""},
    }


# ── Analyst nodes ──────────────────────────────────────────────────────

async def macro_analyst_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    sys = f"""你是 **Macro Analyst**（宏观分析师）。
结合工具返回的 `evidence` / `confidence` 做判断；缺失数据要明确写出。
可调用工具：get_market_data、get_kline_chart、stock_selector、probe_ticker（校验标的覆盖）、get_cn_longhu_for_symbol（A 股龙虎榜本地库）、get_research_pipeline_status（Qlib/RD/门禁链路摘要）、get_tdx_local_snapshot（本机通达信离线 lday/板块/gbbq，需 TDX_ROOT_PATH）；
stock_selector 的 criteria.market 仅允许 CN|US|HK|CRYPTO。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n用户问题: {state.get('query')}\n"
        f"Supervisor 备忘:\n{state.get('supervisor_memo', '')}"
    )
    report = await react_with_tools(llm, TOOLS_COMMON, system=sys, user=user)
    return {"macro_report": report}


async def fundamental_analyst_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    sys = f"""你是 **Fundamental Analyst**（基本面分析师）。
侧重盈利质量、估值锚、行业位置；所有数字必须来自工具结果或其明确推导。
A 股请优先调用 get_cn_financial_statements / get_cn_research_reports；可辅以 get_qlib_factor_snapshot（需平台开启 Qlib）、get_yanbao_market_digest（研报聚合库）、get_tdx_local_snapshot（股本变迁 gbbq、离线日线，需本机通达信与 TDX_ROOT_PATH）；其它市场用 get_market_data、get_kline_chart、stock_selector，不得编造未覆盖市场的财报细节。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n用户问题: {state.get('query')}\n"
        f"宏观摘要:\n{state.get('macro_report', '')[:4000]}"
    )
    report = await react_with_tools(llm, TOOLS_FUNDAMENTAL, system=sys, user=user)
    return {"fundamental_report": report}


async def technical_analyst_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    sys = f"""你是 **Technical Analyst**（技术分析师）。
基于 OHLCV 描述趋势/关键位/波动；引用工具 JSON 中的字段名；仅解读支持市场内标的之 K 线。
可调用工具：get_market_data、get_kline_chart、stock_selector、get_cn_longhu_for_symbol（资金异动线索）、get_qlib_factor_snapshot（ENABLE_QLIB 时与 Qlib 因子序列交叉验证）、get_tdx_local_snapshot（本机通达信离线日线尾部与板块，可与在线 K 线对照）。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n用户问题: {state.get('query')}\n"
        f"基本面摘要:\n{state.get('fundamental_report', '')[:3000]}"
    )
    report = await react_with_tools(llm, TOOLS_TECHNICAL, system=sys, user=user)
    return {"technical_report": report}


async def sentiment_analyst_node(
    state: ResearchState, llm: Any, fingpt_svc: Any
) -> dict[str, Any]:
    sys = f"""你是 **Sentiment Analyst**（情绪与资金偏好分析师）。
可调用工具：stock_selector、get_market_data、get_user_watchlist、get_stock_news、get_yanbao_market_digest；选股 criteria.market 仅限 CN|US|HK|CRYPTO。
事件与舆情请结合 get_stock_news 的 `items` / `relevance_score` / `filter_mode`；调用 get_user_watchlist 时 **必须** 传入整数 user_id={state.get("user_id")}（来自 state，勿编造）。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n用户问题: {state.get('query')}\n"
        f"技术摘要:\n{state.get('technical_report', '')[:2500]}"
    )
    report = await react_with_tools(llm, TOOLS_SENTIMENT, system=sys, user=user)
    if fingpt_svc and fingpt_svc.can_write_research_sentiment() and (report or "").strip():
        t = str(state.get("ticker") or "").strip()
        if t:
            try:
                from app.modules.ai_agent.services.sentiment_fingpt_payload import (
                    build_sentiment_payload_from_analyst_report,
                )
                payload = build_sentiment_payload_from_analyst_report(report)
                payload["source"] = "research_graph"
                payload["source_ref"] = "sentiment_analyst"
                rec = fingpt_svc.record_sentiment(t, payload)
                if not rec.get("ok"):
                    logger.warning("FinGPT record_sentiment (sentiment_analyst) not ok: %s", rec.get("error"))
            except Exception as exc:
                logger.exception("FinGPT sentiment persist failed: %s", exc)
    return {"sentiment_report": report}


async def backtest_optimizer_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    from ..catalog import strategy_catalog_text
    catalog = strategy_catalog_text()
    sys = f"""你是 **Backtest Optimizer**（回测优化师）。
你必须多次调用 **run_backtest** 工具，在以下策略 id 中选择 **至少 5 个不同策略** 做对比（可分批调用）：
{catalog}

每次 run_backtest 传入: strategy_name（上表之一）、ticker（使用 state 中的标的）、params 可含 start/end。
在 **ENABLE_QLIB** 开启时，应至少调用一次 **run_qlib_unified_backtest**（与平台统一 Qlib 买入持有 metrics / `backtest_engine` 对齐），并与多策略回测结论对照说明差异来源。
对 A 股可辅以 **get_tdx_local_snapshot**（本机通达信离线日线，需 ``TDX_ROOT_PATH``）与回测所用行情来源对照。
也可调用 stock_selector（如 smart）做交叉验证。
所有绩效对比必须引用工具返回的 metrics / trades / evidence / confidence；不得编造夏普、收益。
**回测主路径以 A 股（CN）历史为主**；若标的为 HK/US/CRYPTO，须在结论中依据工具 `evidence` 说明数据可用性边界。

{_suffix()}
"""
    user = (
        f"ticker={state.get('ticker')}\nuser_id={state.get('user_id')}\nquery={state.get('query')}\n"
        f"情绪摘要:\n{state.get('sentiment_report', '')[:2000]}"
    )
    report = await react_with_tools(llm, TOOLS_BACKTEST, system=sys, user=user, max_rounds=12)
    return {"backtest_report": report}


# ── Debate nodes ───────────────────────────────────────────────────────

from ..debate_bus import publish_debate_round
from ..state import merge_investment_history, merge_risk_history


async def bull_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    iv = state.get("investment_debate_state") or {}
    sys = f"""你是 **Bull Researcher**（看涨辩论方）。
基于前序分析师与回测报告，提出最强看涨逻辑；如工具证据不足须承认不确定性。
论点须与「支持市场」及已返回工具 evidence 一致；不得引入未覆盖市场叙事。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n问题: {state.get('query')}\n"
        f"宏观:\n{state.get('macro_report', '')[:2000]}\n"
        f"基本面:\n{state.get('fundamental_report', '')[:2000]}\n"
        f"技术:\n{state.get('technical_report', '')[:1500]}\n"
        f"情绪:\n{state.get('sentiment_report', '')[:1500]}\n"
        f"回测:\n{state.get('backtest_report', '')[:4000]}\n"
        f"历史辩论:\n{iv.get('history', '')[-6000:]}"
    )
    chunk = await react_with_tools(llm, [], system=sys, user=user, max_rounds=1)
    new_iv = merge_investment_history(iv, "bull_history", chunk)
    turn = int(state.get("debate_turn") or 0) + 1
    publish_debate_round(
        ticker=str(state.get("ticker") or ""),
        agent_role="bull",
        chunk=chunk,
        round_num=turn,
        debate_phase="investment",
    )
    return {"investment_debate_state": new_iv, "debate_turn": turn}


async def bear_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    iv = state.get("investment_debate_state") or {}
    sys = f"""你是 **Bear Researcher**（看跌辩论方）。
针对 Bull 论点逐条反驳；引用回测逆风场景、宏观/情绪风险；不得无视工具已给出的低 confidence 信号。
反驳须落在支持市场范围内；勿用虚构监管或境外数据攻击对方论点。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n问题: {state.get('query')}\n"
        f"Bull 最近观点:\n{iv.get('bull_history', '')[-4000:]}\n"
        f"回测摘录:\n{state.get('backtest_report', '')[:3000]}"
    )
    chunk = await react_with_tools(llm, [], system=sys, user=user, max_rounds=1)
    new_iv = merge_investment_history(iv, "bear_history", chunk)
    turn = int(state.get("debate_turn") or 0) + 1
    publish_debate_round(
        ticker=str(state.get("ticker") or ""),
        agent_role="bear",
        chunk=chunk,
        round_num=turn,
        debate_phase="investment",
    )
    return {"investment_debate_state": new_iv, "debate_turn": turn}


async def risky_analyst_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    rd = state.get("risk_debate_state") or {}
    sys = f"""你是 **Risk-Seeking Analyst**（进取风险辩方）。
主张在可控回撤下进取暴露；需引用回测最大回撤、波动等（来自上文 backtest_report 文本）。
不得鼓励超出支持市场工具能力的高杠杆「确定性」表述。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n投资辩论历史:\n"
        f"{(state.get('investment_debate_state') or {}).get('history', '')[-5000:]}"
    )
    chunk = await react_with_tools(llm, [], system=sys, user=user, max_rounds=1)
    new_rd = merge_risk_history(rd, "risky_history", chunk)
    rt = int(state.get("risk_debate_turn") or 0) + 1
    publish_debate_round(
        ticker=str(state.get("ticker") or ""),
        agent_role="risky_analyst",
        chunk=chunk,
        round_num=rt,
        debate_phase="risk",
    )
    return {"risk_debate_state": new_rd, "risk_debate_turn": rt}


async def safe_analyst_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    rd = state.get("risk_debate_state") or {}
    sys = f"""你是 **Risk-Averse Analyst**（保守风险辩方）。
强调资本保全、流动性与尾部风险；可要求缩小仓位或对冲。
提醒用户工具覆盖市场边界（CN/HK/US/CRYPTO）及回测数据可能的不完整。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n"
        f"Risk-Seeking 观点:\n{rd.get('risky_history', '')[-4000:]}\n"
        f"回测摘录:\n{state.get('backtest_report', '')[:2500]}"
    )
    chunk = await react_with_tools(llm, [], system=sys, user=user, max_rounds=1)
    new_rd = merge_risk_history(rd, "safe_history", chunk)
    rt = int(state.get("risk_debate_turn") or 0) + 1
    publish_debate_round(
        ticker=str(state.get("ticker") or ""),
        agent_role="safe_analyst",
        chunk=chunk,
        round_num=rt,
        debate_phase="risk",
    )
    return {"risk_debate_state": new_rd, "risk_debate_turn": rt}


# ── Risk Manager & Decision ────────────────────────────────────────────

async def risk_manager_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    sys = f"""你是 **Risk Manager**（终审风险官）。
综合全部材料给出：1) 主要风险清单 2) 建议仓位区间（定性即可）3) 监控指标。
可调用工具：仅 get_user_watchlist(user_id)（**user_id 必须为** {state.get("user_id")}）。
结论须与辩论及回测 evidence 对齐；勿输出与工具矛盾的具体收益数字；结论须显式对齐支持市场范围。
{_suffix()}
"""
    user = (
        f"标的: {state.get('ticker')}\n问题: {state.get('query')}\n"
        f"投资辩论:\n{(state.get('investment_debate_state') or {}).get('history', '')[-6000:]}\n"
        f"风险辩论:\n{(state.get('risk_debate_state') or {}).get('history', '')[-5000:]}\n"
        f"回测:\n{state.get('backtest_report', '')[:4000]}"
    )
    from app.tools.quant_tools import get_user_watchlist
    report = await react_with_tools(
        llm,
        [get_user_watchlist],
        system=sys,
        user=user,
        max_rounds=6,
    )
    return {"risk_manager_report": report}


async def decision_dashboard_node(state: ResearchState, llm: Any) -> dict[str, Any]:
    from ..dashboard_prompt import DECISION_DASHBOARD_SYSTEM_PROMPT, DECISION_DASHBOARD_USER_TEMPLATE
    user = DECISION_DASHBOARD_USER_TEMPLATE.format(
        ticker=state.get("ticker"),
        query=state.get("query"),
        macro_report=state.get("macro_report", ""),
        fundamental_report=state.get("fundamental_report", ""),
        technical_report=state.get("technical_report", ""),
        sentiment_report=state.get("sentiment_report", ""),
        backtest_report=state.get("backtest_report", ""),
        risk_manager_report=state.get("risk_manager_report", ""),
        fingpt_forecast=state.get("fingpt_forecast", ""),
    )
    report = await react_with_tools(
        llm,
        [],
        system=DECISION_DASHBOARD_SYSTEM_PROMPT,
        user=user,
        max_rounds=1,
    )
    return {"decision_dashboard": report}


# ── Chart Vision ───────────────────────────────────────────────────────

async def chart_vision_node(state: ResearchState) -> dict[str, Any]:
    ticker = state.get("ticker", "")
    if not ticker:
        return {"chart_vision_report": "No ticker provided for vision analysis"}
    try:
        from app.modules.ai_agent.services.vision.chart_vision_agent_service import ChartVisionAgentService
        from app.modules.market_data.services.stock_service import StockApplicationService
        from app.modules.system.services.helpers.market_data_provider import get_market_data_provider

        market_provider = get_market_data_provider()
        stock_service = StockApplicationService(market_provider=market_provider)
        vision_service = ChartVisionAgentService(stock_service=stock_service)

        result = await asyncio.to_thread(
            vision_service.analyze,
            symbol=ticker,
            market="CN",
            days=120,
            indicators=["ma5", "ma20", "ma60"],
        )

        if result.get("status") != "success":
            return {
                "chart_vision_report": f"Vision analysis failed: {result.get('message', 'unknown')}",
                "chart_vision_signal": "neutral",
                "chart_vision_confidence": 0.0,
            }

        merged = result.get("merged_signal", {})
        visual = result.get("visual_analysis", {})
        numerical = result.get("numerical_analysis", {})

        patterns_desc = []
        for p in visual.get("patterns", []):
            patterns_desc.append(f"{p.get('name','?')} ({p.get('confidence',0):.0%}, {p.get('direction','?')})")

        num_descs = []
        for k, v in sorted(numerical.get("signals", {}).items()):
            num_descs.append(f"{k}: {v.get('signal','?')} ({v.get('confidence',0):.0%})")

        report = "Chart-Vision:\n"
        report += "Patterns: " + ", ".join(patterns_desc) + "\n"
        report += "Numerical: " + ", ".join(num_descs) + "\n"

        return {
            "chart_vision_report": report,
            "chart_vision_signal": merged.get("signal", "neutral"),
            "chart_vision_confidence": merged.get("confidence", 0.0),
            "chart_vision_patterns": [p.get("name") for p in visual.get("patterns", [])],
        }
    except Exception as exc:
        logger.debug("chart_vision_node error: %s", exc, exc_info=True)
        return {
            "chart_vision_report": f"Chart-Vision Agent error: {exc}",
            "chart_vision_signal": "neutral",
            "chart_vision_confidence": 0.0,
        }


# ── Evidence write node ────────────────────────────────────────────────

async def write_fundamental_evidence(state: ResearchState) -> dict[str, Any]:
    from ...constants import BlackboardKey
    from ...evidence_blackboard import (
        EvidenceStrength,
        EvidenceType,
        get_evidence_blackboard,
    )

    bb = get_evidence_blackboard()
    bb.write(
        agent_name="fundamental_analyst",
        key=str(BlackboardKey.FUNDAMENTALS),
        value=state.get("fundamental_report", "")[:1000],
        evidence_type=EvidenceType.FUNDAMENTAL,
        strength=EvidenceStrength.MODERATE,
    )
    return {}


async def write_macro_evidence(state: ResearchState) -> dict[str, Any]:
    from ...constants import AgentName, BlackboardKey
    from ...evidence_blackboard import (
        EvidenceStrength,
        EvidenceType,
        get_evidence_blackboard,
    )

    bb = get_evidence_blackboard()
    bb.write(
        agent_name=str(AgentName.MACRO_ANALYST),
        key=str(BlackboardKey.PRICE_HISTORY),
        value=state.get("macro_report", "")[:1000],
        evidence_type=EvidenceType.MACRO,
        strength=EvidenceStrength.MODERATE,
    )
    return {}
