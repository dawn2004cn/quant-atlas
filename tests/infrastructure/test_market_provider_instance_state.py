from app.infrastructure.providers.market_data import MultiSourceMarketProvider


class _CountingTdx:
    def __init__(self):
        self.connected = True

    @property
    def is_available(self) -> bool:
        return True

    @property
    def is_connected(self) -> bool:
        return self.connected

    def reconnect(self) -> None:
        self.connected = True

    def execute(self, method: str, *args):
        return []


def test_provider_tdx_adapter_isolated_per_instance():
    counter = {"value": 0}

    def factory():
        counter["value"] += 1
        return _CountingTdx()

    provider_a = MultiSourceMarketProvider(tdx_factory=factory)
    provider_b = MultiSourceMarketProvider(tdx_factory=factory)

    _ = provider_a._get_tdx()
    _ = provider_a._get_tdx()
    _ = provider_b._get_tdx()

    assert counter["value"] == 2
