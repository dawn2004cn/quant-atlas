from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PsychologyEvent:
    event_id: str
    user_id: int
    event_type: str  # panic_sell / fomo_buy / revenge_trade / overtrade
    symbol: str
    severity: float  # 0..1
    context: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class PsychologyReport:
    user_id: int
    total_events: int = 0
    panic_sells: int = 0
    fomo_buys: int = 0
    revenge_trades: int = 0
    overtrades: int = 0
    score: float = 1.0
    recommendations: list[str] = field(default_factory=list)


class PsychologyTrackerService:
    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "psychology_events.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)

    def record_event(
        self,
        user_id: int,
        event_type: str,
        symbol: str,
        severity: float = 0.5,
        context: dict | None = None,
    ) -> PsychologyEvent:
        event = PsychologyEvent(
            event_id=f"psy.{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            event_type=event_type,
            symbol=symbol,
            severity=min(1.0, max(0.0, severity)),
            context=context or {},
        )
        with self._store.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.__dict__, ensure_ascii=False) + "\n")
        return event

    def get_report(self, user_id: int, days: int = 30) -> PsychologyReport:
        events = self._load_events(user_id, days)
        report = PsychologyReport(user_id=user_id, total_events=len(events))
        for e in events:
            if e.event_type == "panic_sell":
                report.panic_sells += 1
            elif e.event_type == "fomo_buy":
                report.fomo_buys += 1
            elif e.event_type == "revenge_trade":
                report.revenge_trades += 1
            elif e.event_type == "overtrade":
                report.overtrades += 1
        report.score = max(
            0.0,
            1.0
            - (
                report.panic_sells * 0.1
                + report.fomo_buys * 0.08
                + report.revenge_trades * 0.15
                + report.overtrades * 0.05
            ),
        )
        if report.panic_sells > 3:
            report.recommendations.append(
                "检测到多次恐慌抛售，建议设置自动止损单避免情绪化决策"
            )
        if report.fomo_buys > 3:
            report.recommendations.append("检测到追高行为，建议在买入前等待至少 15 分钟冷静期")
        return report

    def _load_events(self, user_id: int, days: int) -> list[PsychologyEvent]:
        if not Path(self._store).exists():
            return []
        events = []
        with open(self._store, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                event = PsychologyEvent(**json.loads(line))
                if event.user_id == user_id:
                    events.append(event)
        return events

