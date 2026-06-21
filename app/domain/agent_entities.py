from __future__ import annotations
"""Domain entities for AI agents (QuantML-Agent port)."""


import json
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Any


@dataclass
class MarketInsight:
    id: int | None = None
    market: str = ""
    sentiment_score: float = 0.0
    sentiment_label: str = "Neutral"
    trend_prediction: str = ""
    hot_sectors: list[str] = field(default_factory=list)
    full_analysis: str = ""
    created_at: datetime | None = None


@dataclass
class ReportInterpretation:
    id: int | None = None
    report_title: str = ""
    source: str | None = None
    report_date: date | None = None
    summary: str = ""
    key_takeaways: list[str] = field(default_factory=list)
    market_impact: str = "Low"
    full_interpretation: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class ExpertSkill:
    name: str
    description: str
    category: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmAgentSpec:
    id: str
    role: str
    system_prompt: str
    tools: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


@dataclass
class SwarmTask:
    id: str
    agent_id: str
    status: str
    summary: str | None = None
    error: str | None = None
    artifacts: list[str] = field(default_factory=list)


@dataclass
class SwarmRun:
    id: str
    preset_name: str
    status: str
    topic: str
    final_report: str | None = None
    tasks: list[SwarmTask] = field(default_factory=list)
    created_at: datetime | None = None
    completed_at: datetime | None = None
