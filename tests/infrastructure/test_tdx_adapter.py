from app.infrastructure.adapters.legacy_tdx_adapter import LegacyTdxAdapter


def test_legacy_tdx_adapter_has_required_interface():
    adapter = LegacyTdxAdapter()
    assert hasattr(adapter, "is_available")
    assert hasattr(adapter, "is_connected")
    assert hasattr(adapter, "reconnect")
    assert hasattr(adapter, "execute")
