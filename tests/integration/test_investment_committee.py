"""测试 AI 投资委员会"""

from dotenv import load_dotenv

load_dotenv()


def test_strategy_library():
    """测试策略库"""
    print("=== 测试策略库 ===\n")

    from app.infrastructure.agent.investment_committee import StrategyLibrary

    lib = StrategyLibrary()

    print("十大天王策略:")
    all_strategies = lib.get_all_strategies()
    for category, strategies in all_strategies.items():
        print(f"\n{category}:")
        for i, s in enumerate(strategies, 1):
            print(f"  {i}. {s}")


def test_market_regime():
    """测试市场状态分析"""
    print("\n=== 测试市场状态分析 ===\n")

    from app.infrastructure.agent.investment_committee import AIInvestmentCommittee, MarketIndex
    from app.infrastructure.agent.investment_committee_db import MarketDataProvider

    committee = AIInvestmentCommittee()
    market_data = MarketDataProvider()

    # 获取上证指数数据
    print("获取上证指数数据...")
    df = market_data.get_index_data("000001.SH", days=250)
    import pandas as pd
    if not isinstance(df, pd.DataFrame) or df.empty:
        print("无法获取数据，使用模拟数据")
        # 创建模拟数据
        import numpy as np
        dates = pd.date_range(end="2024-12-31", periods=250, freq="D")
        close = np.cumsum(np.random.randn(250)) + 3000
        df = pd.DataFrame({
            "Close": close,
            "High": close * 1.02,
            "Low": close * 0.98,
            "Open": close,
        })

    print(f"获取到 {len(df)} 条数据")

    # 分析
    result = committee.analyze_markets({MarketIndex.SHANGHAI: df})

    print(f"\n市场状态: {result.overall_regime.value}")
    print(f"风险等级: {result.risk_level}")
    print(f"推荐策略: {result.recommended_strategies}")

    for idx, state in result.markets.items():
        print(f"\n{idx.value}:")
        print(f"  状态: {state.regime.value}")
        print(f"  置信度: {state.confidence:.2f}")
        print(f"  ADX: {state.adx:.2f}")


def test_committee_agents():
    """测试各 Agent"""
    print("\n=== 测试投资委员会 Agent ===\n")

    from app.infrastructure.agent.investment_committee_service import (
        create_committee_service,
        MacroAgent,
        ChenXiaoQunAgent,
    )

    # 测试单个 Agent
    macro = MacroAgent("宏观分析师")
    opinion = macro.analyze({
        "market_analysis": {
            "overall_regime": "牛市",
            "risk_level": "medium"
        }
    })
    print(f"{opinion.agent_name}: {opinion.opinion}")

    # 测试陈小群
    chenshaoqun = ChenXiaoQunAgent()
    opinion = chenshaoqun.analyze({
        "market_analysis": {
            "overall_regime": "震荡市",
            "risk_level": "low"
        }
    })
    print(f"\n{opinion.agent_name}: {opinion.opinion}")


def test_trade_recorder():
    """测试交易记录"""
    print("\n=== 测试交易记录 ===\n")

    from app.infrastructure.agent.investment_committee_db import TradeRecorder

    recorder = TradeRecorder()

    # 测试保存交易
    test_trade = {
        "symbol": "000001",
        "name": "平安银行",
        "strategy": "米勒维尼 VCP",
        "direction": "buy",
        "price": 12.50,
        "quantity": 10000,
        "amount": 125000,
        "trade_time": "2024-01-15 10:30:00",
        "status": "holding",
    }

    record_id = recorder.save_trade(test_trade)
    print(f"保存交易记录 ID: {record_id}")

    # 获取持仓
    positions = recorder.get_open_positions()
    print(f"当前持仓: {len(positions)}")


def test_full_committee():
    """测试完整投资委员会"""
    print("\n=== 测试完整投资委员会 ===\n")

    from app.infrastructure.agent.investment_committee_service import create_committee_service

    print("创建投资委员会服务...")
    service = create_committee_service()

    print("运行分析...")
    decision = service.run_analysis()

    print(f"\n=== 决策结果 ===")
    print(f"市场状态: {decision.overall_regime}")
    print(f"风险等级: {decision.risk_level}")
    print(f"选股数量: {len(decision.selected_stocks)}")
    print(f"交易决策: {len(decision.trade_decisions)}")
    print(f"\n决策理由: {decision.reasoning}")

    print(f"\n=== Agent 意见 ===")
    for opinion in decision.agent_opinions:
        print(f"- {opinion.agent_name}: {opinion.opinion[:50]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("AI 投资委员会测试")
    print("=" * 60)

    test_strategy_library()
    test_market_regime()
    test_committee_agents()
    test_trade_recorder()
    # test_full_committee()  # 需要较长时间

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)