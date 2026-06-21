from app.presentation.api.response_builders import build_success_payload, with_legacy_aliases


def test_build_success_payload_with_meta():
    payload = build_success_payload(data=[1, 2], meta={"count": 2})
    assert payload["status"] == "success"
    assert payload["data"] == [1, 2]
    assert payload["meta"]["count"] == 2


def test_build_success_payload_without_meta():
    payload = build_success_payload(data={"ok": True})
    assert payload == {"status": "success", "data": {"ok": True}}


def test_with_legacy_aliases_enabled():
    payload = build_success_payload(data=[1, 2], meta={"count": 2})
    mapped = with_legacy_aliases(payload, alias_key="stocks", enabled=True)
    assert mapped["stocks"] == [1, 2]
    assert mapped["data"] == [1, 2]


def test_with_legacy_aliases_disabled():
    payload = build_success_payload(data=[1, 2], meta={"count": 2})
    mapped = with_legacy_aliases(payload, alias_key="stocks", enabled=False)
    assert "stocks" not in mapped
