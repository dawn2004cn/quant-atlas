from app.infrastructure.mappers.symbol_normalizer import SymbolNormalizer


def test_symbol_normalizer_sh_main_board():
    assert SymbolNormalizer.normalize_code("600519") == "600519"
    assert SymbolNormalizer.market_id("600519") == 1
    assert SymbolNormalizer.normalized_with_prefix("600519") == "sh600519"


def test_symbol_normalizer_sz_main_board():
    assert SymbolNormalizer.normalize_code("000001") == "000001"
    assert SymbolNormalizer.market_id("000001") == 0
    assert SymbolNormalizer.normalized_with_prefix("000001") == "sz000001"


def test_symbol_normalizer_star_market():
    assert SymbolNormalizer.market_id("688001") == 1
    assert SymbolNormalizer.normalized_with_prefix("688001") == "sh688001"


def test_symbol_normalizer_handles_mixed_input():
    assert SymbolNormalizer.normalize_code("sz000001") == "000001"
    assert SymbolNormalizer.normalized_with_prefix("sz000001") == "sz000001"


def test_symbol_normalizer_strips_cn_prefix():
    assert SymbolNormalizer.to_db_code("CN:sh600519") == "sh600519"
    assert SymbolNormalizer.to_db_code("CN:600519") == "sh600519"
    assert SymbolNormalizer.from_db_code("CN:sz000001") == "sz000001"


def test_symbol_normalizer_api_helpers():
    assert SymbolNormalizer.to_api_code("600519") == "sh600519"
    assert SymbolNormalizer.to_code6("sh600519") == "600519"
    assert SymbolNormalizer.to_display("600519") == "沪A600519"
    assert SymbolNormalizer.to_display("000001") == "深A000001"
    assert SymbolNormalizer.is_valid("600519") is True
    assert SymbolNormalizer.is_valid("000000") is False
    assert SymbolNormalizer.to_full_code("600519") == "sh600519"

    parsed = SymbolNormalizer.parse_input("600519")
    assert parsed["code6"] == "600519"
    assert parsed["market"] == "sh"
    assert parsed["cn_symbol"] == "sh600519"
    assert parsed["db_code"] == "sh600519"
    assert parsed["display"] == "沪A600519"
