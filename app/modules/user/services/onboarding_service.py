
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[5] / "instance"
FILE = BASE / "onboarding_progress.jsonl"

STEPS = [
    {"id":"registered","label":"注册完成","label_en":"Registration Complete"},
    {"id":"first_login","label":"首次登录","label_en":"First Login"},
    {"id":"watchlist_created","label":"创建自选股","label_en":"Watchlist Created"},
    {"id":"market_viewed","label":"查看行情","label_en":"Market Data Viewed"},
    {"id":"first_backtest","label":"首次回测","label_en":"First Backtest"},
    {"id":"first_ai_analysis","label":"首次AI分析","label_en":"First AI Analysis"},
    {"id":"first_trade_signal","label":"首次交易信号","label_en":"First Trade Signal"},
    {"id":"first_investment","label":"首次调仓","label_en":"First Investment"},
]

class OnboardingService:
    def __init__(self):
        BASE.mkdir(parents=True, exist_ok=True)

    def _load(self, uid: str) -> dict:
        if not FILE.exists():
            return {}
        try:
            with open(FILE, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        e = json.loads(line)
                        if e.get("user_id") == uid:
                            return e
                    except json.JSONDecodeError:
                        continue
        except OSError:
            pass
        return {}

    def _save(self, entry: dict) -> None:
        existing = []
        if FILE.exists():
            try:
                with open(FILE, encoding="utf-8") as f:
                    existing = [json.loads(l) for l in f if l.strip()]
            except (OSError, json.JSONDecodeError):
                existing = []
        existing = [e for e in existing if e.get("user_id") != entry["user_id"]]
        existing.append(entry)
        with open(FILE, "w", encoding="utf-8") as f:
            for e in existing:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def get_progress(self, uid: str) -> dict:
        entry = self._load(uid)
        completed = set(entry.get("completed_steps", []))
        current = None
        for s in STEPS:
            if s["id"] not in completed:
                current = s["id"]
                break
        return {
            "user_id": uid,
            "completed_steps": list(completed),
            "completed_count": len(completed),
            "total_steps": len(STEPS),
            "current_step": current or "completed",
            "is_complete": current is None,
            "progress_pct": round(len(completed) / len(STEPS) * 100, 1),
        }

    def complete_step(self, uid: str, step_id: str) -> dict:
        if not step_id:
            return self.get_progress(uid)
        entry = self._load(uid)
        completed = set(entry.get("completed_steps", []))
        if step_id not in completed:
            completed.add(step_id)
            entry["user_id"] = uid
            entry["completed_steps"] = list(completed)
            entry["updated_at"] = datetime.now().isoformat()
            self._save(entry)
        return self.get_progress(uid)

    def list_steps(self) -> list:
        return STEPS
