from pathlib import Path


def test_tdx_lday_file_infers_sh_for_68_prefix():
    from app.infrastructure.tdx_local.paths import TdxLocalPaths

    root = Path("E:/TDX")
    p = TdxLocalPaths(root=root).lday_file(market_sh=False, code6="689001")
    assert str(p).replace("\\", "/").endswith("/vipdoc/sh/lday/sh689001.day")


def test_tdx_lday_file_infers_bj_for_43_prefix():
    from app.infrastructure.tdx_local.paths import TdxLocalPaths

    root = Path("E:/TDX")
    p = TdxLocalPaths(root=root).lday_file(market_sh=False, code6="430047")
    assert str(p).replace("\\", "/").endswith("/vipdoc/bj/lday/bj430047.day")

