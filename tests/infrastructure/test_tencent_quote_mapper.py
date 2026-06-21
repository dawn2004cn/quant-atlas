from app.domain.enums import MarketCode
from app.infrastructure.mappers.tencent_quote_mapper import TencentQuoteMapper


def test_mapper_parses_valid_line():
    line = 'v_sz000001="51~平安银行~000001~12.34~12.00~12.01~1000~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~2.83~12.60~12.10~0~0~123456789~0~1.23~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";'
    quote = TencentQuoteMapper.parse_line(line, MarketCode.CN)
    assert quote is not None
    assert quote.code == "000001"
    assert quote.price == 12.34


def test_mapper_ignores_dirty_line():
    assert TencentQuoteMapper.parse_line("random text", MarketCode.CN) is None


def test_mapper_ignores_short_line():
    short_line = 'v_sz000001="51~平安银行~000001";'
    assert TencentQuoteMapper.parse_line(short_line, MarketCode.CN) is None


def test_mapper_ignores_non_numeric_line():
    bad_numeric = 'v_sz000001="51~平安银行~000001~abc~12.00~12.01~1000~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~2.83~12.60~12.10~0~0~123456789~0~1.23~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";'
    assert TencentQuoteMapper.parse_line(bad_numeric, MarketCode.CN) is None
