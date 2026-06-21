from app.tools.quant_tools import list_quant_tool_names, quant_tools_agent_system_suffix


def test_list_quant_tool_names_sorted_unique():
    names = list_quant_tool_names()
    assert names == tuple(sorted(names))
    assert "get_market_data" in names
    assert "run_backtest" in names


def test_quant_tools_agent_system_suffix_contains_markets_and_tools():
    s = quant_tools_agent_system_suffix()
    assert "CN" in s and "HK" in s and "US" in s and "CRYPTO" in s
    for n in list_quant_tool_names():
        assert n in s
