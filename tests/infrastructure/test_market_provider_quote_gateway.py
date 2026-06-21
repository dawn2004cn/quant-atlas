from app.domain.enums import MarketCode
from app.infrastructure.providers.market_data import MultiSourceMarketProvider


class _FakeQuoteGateway:
    def fetch_quotes_text(self, normalized_symbols, timeout):
        return 'v_sz000001="51~平安银行~000001~12.34~12.00~12.01~1000~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~2.83~12.60~12.10~0~0~123456789~0~1.23~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0~0";'


def test_market_provider_parses_quotes_via_gateway():
    provider = MultiSourceMarketProvider(quote_gateway=_FakeQuoteGateway())
    provider._cache.save_stocks = lambda rows: None
    quotes = provider.get_realtime_quotes(["000001"], market=MarketCode.CN)
    assert len(quotes) == 1
    assert quotes[0].code == "000001"
    assert quotes[0].name == "平安银行"
    assert quotes[0].price == 12.34
