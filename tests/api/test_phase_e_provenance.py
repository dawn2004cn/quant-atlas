from flask import Flask, jsonify
from app.modules.system.services.ui.decision_provenance_service import DecisionProvenanceService
from app.presentation.api.provenance import with_provenance, _build_provenance_summary


def _make_json_response(data):
    return jsonify(data)


def _subject_factory(*_args, **_kwargs):
    return "600519"


@with_provenance(subject_factory=_subject_factory, model_version="test")
def fake_endpoint():
    payload = {
        "subject": "600519",
        "input_snapshot": {"ts": "2026-06-10"},
        "reasoning_trace": ["t1", "t2"],
        "evidence": [{"source": "tdx", "confidence": 0.9}],
        "result": {"signal": "bullish"},
    }
    return _make_json_response(payload)


def test_provenance_decorator_adds_summary():
    app = Flask(__name__)
    with app.app_context():
        resp = fake_endpoint()
        assert resp.status_code == 200
        data = resp.get_json()
        assert "provenance" in data
        p = data["provenance"]
        assert p["subject"] == "600519"
        assert p["model_version"] == "test"
        assert p["evidence_count"] == 1
        assert p["reasoning_trace"] == ["t1", "t2"]
        assert data["result"]["signal"] == "bullish"


def test_provenance_skips_when_no_subject():
    @with_provenance(subject_factory=lambda *a, **k: "")
    def endpoint():
        return _make_json_response({"ok": True})

    app = Flask(__name__)
    with app.app_context():
        resp = endpoint()
        assert resp.get_json() == {"ok": True}
