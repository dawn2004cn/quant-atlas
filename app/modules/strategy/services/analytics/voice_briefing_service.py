"""Voice Briefing — narrative daily briefing to TTS podcast (Quant Atlas 7.0 Step Four)."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from app.core.logger import get_logger

logger = get_logger(__name__)

_MAX_SCRIPT_CHARS = 3500
_WINNING_OUTCOMES = frozenset({"win", "profit", "success", "correct", "bullish", "positive"})


class VoiceBriefingService:
    """Turn smart-daily narrative into a listenable morning briefing."""

    def __init__(
        self,
        *,
        smart_daily_briefing_service: Any | None = None,
        store_dir: str | Path | None = None,
    ) -> None:
        self._briefing = smart_daily_briefing_service
        root = Path(__file__).resolve().parents[4]
        self._store_dir = Path(store_dir or root / "instance" / "voice_briefings")
        self._store_dir.mkdir(parents=True, exist_ok=True)

    def generate_daily(
        self,
        user_id: int,
        *,
        market: str = "CN",
        top_n: int = 3,
        role: str | None = None,
        synthesize_audio: bool = True,
    ) -> dict[str, Any]:
        if self._briefing is None:
            return {"ok": False, "error": "smart_daily_briefing_unavailable"}

        from app.domain.enums import MarketCode

        try:
            mkt = MarketCode(market.upper())
        except ValueError:
            mkt = MarketCode.CN

        briefing = self._briefing.generate_briefing(
            market=mkt,
            top_n=top_n,
            user_id=user_id,
            role=role,
            use_narrative=True,
        )
        if not briefing.get("ok"):
            return briefing

        script = self._build_script(briefing)
        result: dict[str, Any] = {
            "ok": True,
            "briefing_date": briefing.get("briefing_date"),
            "narrative_mode": briefing.get("narrative_mode"),
            "script": script,
            "script_chars": len(script),
            "duration_estimate_sec": max(30, len(script) // 5),
            "recommendations": briefing.get("recommendations") or [],
            "summary": briefing.get("summary"),
        }

        if synthesize_audio:
            audio = self._synthesize_tts(script, user_id=user_id)
            result.update(audio)

        return result

    def get_audio_path(self, file_id: str) -> Path | None:
        safe = "".join(ch for ch in file_id if ch.isalnum() or ch in "-_")
        if not safe or safe != file_id:
            return None
        path = self._store_dir / f"{safe}.mp3"
        return path if path.is_file() else None

    def _build_script(self, briefing: dict[str, Any]) -> str:
        parts: list[str] = []
        narrative = briefing.get("narrative") or {}
        opening = str(narrative.get("opening") or "").strip()
        market_narr = str(narrative.get("market_narrative") or "").strip()
        closing = str(narrative.get("personalized_closing") or "").strip()
        summary = str(briefing.get("summary") or "").strip()

        if opening:
            parts.append(opening)
        elif summary:
            parts.append(f"早安，这是您的 Quant Atlas 投研晨间简报。{summary}")
        else:
            parts.append("早安，这是您的 Quant Atlas 投研晨间简报。")

        env = briefing.get("market_environment") or {}
        regime_desc = str(env.get("regime_description") or env.get("regime") or "").strip()
        if market_narr:
            parts.append(market_narr)
        elif regime_desc:
            parts.append(f"当前市况：{regime_desc}")

        hooks = narrative.get("causal_hooks") or []
        for hook in hooks[:2]:
            text = str(hook).strip()
            if text:
                parts.append(text)

        recs = briefing.get("recommendations") or []
        if recs:
            parts.append("今日精选标的如下。")
            for idx, rec in enumerate(recs[:5], start=1):
                sym = rec.get("symbol") or rec.get("code") or ""
                name = rec.get("name") or sym
                narr = str(rec.get("narrative") or "").strip()
                reasons = rec.get("reasons") or []
                if narr:
                    parts.append(f"第{idx}只，{name}。{narr}")
                elif reasons:
                    parts.append(f"第{idx}只，{name}。{reasons[0]}")
                else:
                    parts.append(f"第{idx}只，{name}。")

        if closing:
            parts.append(closing)
        else:
            parts.append("以上仅供参考，请独立判断并自担风险。祝您交易顺利。")

        script = "\n".join(parts)
        if len(script) > _MAX_SCRIPT_CHARS:
            script = script[: _MAX_SCRIPT_CHARS - 20] + "……（简报已截断）"
        return script

    def _resolve_tts_llm_config(self, user_id: int) -> dict[str, str | None]:
        try:
            from app.core.llm_config import LLMFactory
            config = LLMFactory.get_config()
            return {"api_key": config.api_key if config.api_key != "EMPTY" else None, "base_url": config.base_url}
        except Exception:
            return {"api_key": None, "base_url": None}

    def _synthesize_tts(self, script: str, *, user_id: int) -> dict[str, Any]:
        llm_config = self._resolve_tts_llm_config(user_id)
        api_key = (llm_config.get("api_key") or os.getenv("OPENAI_API_KEY") or "").strip()
        if not api_key:
            return {
                "audio_mode": "browser",
                "audio_url": None,
                "audio_hint": "未配置 OPENAI_API_KEY，请使用浏览器朗读或配置 TTS。",
            }

        base_url = (
            llm_config.get("base_url")
            or os.getenv("OPENAI_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        voice = (os.getenv("TTS_VOICE") or "nova").strip()
        model = (os.getenv("TTS_MODEL") or "tts-1").strip()
        digest = hashlib.sha256(f"{user_id}:{script[:200]}".encode()).hexdigest()[:16]
        file_id = f"vb-{digest}-{uuid.uuid4().hex[:8]}"
        out_path = self._store_dir / f"{file_id}.mp3"

        try:
            response = requests.post(
                f"{base_url}/audio/speech",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": script, "voice": voice},
                timeout=90,
            )
            if response.status_code >= 400:
                logger.warning("OpenAI TTS failed status=%s body=%s", response.status_code, response.text[:200])
                return {
                    "audio_mode": "browser",
                    "audio_url": None,
                    "audio_hint": f"TTS 服务返回 {response.status_code}，已回退浏览器朗读。",
                }
            out_path.write_bytes(response.content)
            return {
                "audio_mode": "openai",
                "audio_file_id": file_id,
                "audio_url": f"/api/v1/briefing/voice-daily/audio/{file_id}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("voice_briefing TTS error: %s", exc)
            return {
                "audio_mode": "browser",
                "audio_url": None,
                "audio_hint": "TTS 合成失败，已回退浏览器朗读。",
            }


__all__ = ["VoiceBriefingService"]
