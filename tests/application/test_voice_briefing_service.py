from __future__ import annotations

from unittest.mock import MagicMock

from app.modules.strategy.services.analytics.voice_briefing_service import VoiceBriefingService


def test_build_script_from_narrative(tmp_path) -> None:
    briefing_svc = MagicMock()
    briefing_svc.generate_briefing.return_value = {
        "ok": True,
        "briefing_date": "2026-06-06",
        "summary": "今日精选2只",
        "market_environment": {"regime_description": "震荡市"},
        "narrative": {
            "opening": "早安，市场进入震荡节奏。",
            "market_narrative": "资金在高弹性板块轮动。",
            "causal_hooks": ["您上周的抄底模式在长安汽车上重现。"],
            "personalized_closing": "祝您交易顺利。",
        },
        "recommendations": [
            {"symbol": "sz000625", "name": "长安汽车", "narrative": "背离信号值得关注。"},
        ],
    }
    svc = VoiceBriefingService(
        smart_daily_briefing_service=briefing_svc,
        store_dir=tmp_path,
    )
    out = svc.generate_daily(1, synthesize_audio=False)
    assert out["ok"] is True
    assert "早安" in out["script"]
    assert "长安汽车" in out["script"]
    assert "script" in out
    assert out.get("audio_url") is None


def test_tts_fallback_without_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    briefing_svc = MagicMock()
    briefing_svc.generate_briefing.return_value = {
        "ok": True,
        "briefing_date": "2026-06-06",
        "summary": "简报",
        "recommendations": [],
    }
    svc = VoiceBriefingService(smart_daily_briefing_service=briefing_svc, store_dir=tmp_path)
    out = svc.generate_daily(1, synthesize_audio=True)
    assert out["audio_mode"] == "browser"
    assert out.get("audio_url") is None
