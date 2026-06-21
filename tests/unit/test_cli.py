"""app.cli 参数解析（不触网）。"""

from app.cli.main import _parser


def test_cli_subcommands_parse():
    p = _parser()
    a = p.parse_args(["portal-eastmoney", "--limit", "12"])
    assert a.command == "portal-eastmoney"
    assert a.limit == 12
    a2 = p.parse_args(["longhu", "--lookback-days", "3"])
    assert a2.command == "longhu"
    assert a2.lookback == 3
    a3 = p.parse_args(["yanbao"])
    assert a3.command == "yanbao"
    a4 = p.parse_args(["portal-10jqka"])
    assert a4.command == "portal-10jqka"
