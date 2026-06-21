"""Zen-Mode Terminal — Phase 18.1.
Extreme simplification: hides non-essential indicators, provides a single Jarvis-driven semantic search bar.
Adaptive complexity: shows more tools as user expertise grows."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ZenModeConfig:
    """User-specific Zen mode configuration."""
    user_id: int
    zen_enabled: bool = True
    show_kline: bool = True
    show_semantic_search: bool = True
    show_volume: bool = False
    show_indicators: bool = False
    show_news: bool = False
    show_agent_apps: bool = False
    complexity_level: int = 1  # 1-5, auto-evolves with usage
    last_updated: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SemanticSearchResult:
    """Result from unified semantic search across Jarvis, TemporalKG, and Screening."""
    query: str
    result_type: str  # "stock", "pattern", "strategy", "insight"
    symbol: str = ""
    label: str = ""
    description: str = ""
    confidence: float = 0.0
    source: str = ""
    action_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ZenModeService:
    """Zen mode terminal — extreme simplification with adaptive complexity."""

    def __init__(self):
        root = Path(__file__).resolve().parents[4]
        self._store = root / "instance" / "zen_configs.jsonl"
        self._store.parent.mkdir(parents=True, exist_ok=True)
        self._configs: dict[int, ZenModeConfig] = {}

    def get_config(self, user_id: int) -> ZenModeConfig:
        """Get or create Zen mode config for user."""
        if user_id in self._configs:
            return self._configs[user_id]
        config = self._load_config(user_id)
        if config is None:
            config = ZenModeConfig(user_id=user_id)
            self._save_config(config)
        self._configs[user_id] = config
        return config

    def set_zen_mode(self, user_id: int, enabled: bool) -> ZenModeConfig:
        """Toggle Zen mode on/off."""
        config = self.get_config(user_id)
        config.zen_enabled = enabled
        config.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_config(config)
        return config

    def evolve_complexity(self, user_id: int, days_active: int, total_actions: int) -> ZenModeConfig:
        """Auto-evolve complexity level based on user engagement."""
        config = self.get_config(user_id)
        # Complexity grows with engagement
        if days_active > 90 and total_actions > 500:
            config.complexity_level = 5
        elif days_active > 60 and total_actions > 300:
            config.complexity_level = 4
        elif days_active > 30 and total_actions > 100:
            config.complexity_level = 3
        elif days_active > 7 and total_actions > 30:
            config.complexity_level = 2
        else:
            config.complexity_level = 1

        # Auto-toggle features based on complexity
        config.show_indicators = config.complexity_level >= 3
        config.show_volume = config.complexity_level >= 2
        config.show_news = config.complexity_level >= 4
        config.show_agent_apps = config.complexity_level >= 5
        config.last_updated = datetime.now(timezone.utc).isoformat()
        self._save_config(config)
        return config

    def semantic_search(self, query: str, user_id: int = 0, top_k: int = 5) -> list[SemanticSearchResult]:
        """Unified semantic search across Jarvis, TemporalKG, and Screening."""
        results = []
        query_lower = query.lower().strip()

        # 1. Stock symbol search
        if query_lower.isdigit() and len(query_lower) == 6:
            results.append(SemanticSearchResult(
                query=query,
                result_type="stock",
                symbol=query_lower,
                label=f"{query_lower} 股票详情",
                description="查看K线、基本面、技术指标",
                confidence=0.95,
                source="symbol_match",
                action_url=f"/stock/{query_lower}",
            ))

        # 2. Pattern search via TemporalKG
        if any(kw in query_lower for kw in ["走势", "形态", "pattern", "共振", "相似"]):
            results.append(SemanticSearchResult(
                query=query,
                result_type="pattern",
                label="历史走势共振分析",
                description="查找与当前走势最相似的历史片段",
                confidence=0.85,
                source="temporal_kg",
                action_url="/decision-replay-space",
            ))

        # 3. Strategy search
        if any(kw in query_lower for kw in ["策略", "因子", "alpha", "选股", "回测"]):
            results.append(SemanticSearchResult(
                query=query,
                result_type="strategy",
                label="策略与因子搜索",
                description="浏览Alpha策略模板和因子库",
                confidence=0.80,
                source="strategy_wizard",
                action_url="/strategy-wizard",
            ))

        # 4. Sentiment / news
        if any(kw in query_lower for kw in ["情绪", "新闻", "热点", "板块", "sentiment"]):
            results.append(SemanticSearchResult(
                query=query,
                result_type="insight",
                label="市场情绪与热点",
                description="AI情绪解读、板块热度、龙虎榜",
                confidence=0.75,
                source="sentiment_radar",
                action_url="/hot-sectors",
            ))

        # 5. Risk / portfolio
        if any(kw in query_lower for kw in ["风险", "持仓", "portfolio", "组合", "仓位"]):
            results.append(SemanticSearchResult(
                query=query,
                result_type="insight",
                label="组合风险分析",
                description="持仓相关性、风险暴露、免疫对冲建议",
                confidence=0.78,
                source="risk_companion",
                action_url="/risk-companion",
            ))

        # 6. Alpha Marketplace
        if any(kw in query_lower for kw in ["市场", "token", "代币", "因子交易", "购买"]):
            results.append(SemanticSearchResult(
                query=query,
                result_type="strategy",
                label="Alpha 因子市场",
                description="浏览和购买高IC因子Token",
                confidence=0.82,
                source="alpha_marketplace",
                action_url="/alpha-marketplace",
            ))

        return results[:top_k]

    def _load_config(self, user_id: int) -> ZenModeConfig | None:
        if not self._store.exists():
            return None
        with self._store.open("r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                if int(data.get("user_id", -1)) == user_id:
                    return ZenModeConfig(**data)
        return None

    def _save_config(self, config: ZenModeConfig) -> None:
        # Rewrite: remove old entry, append new
        rows = []
        if self._store.exists():
            with self._store.open("r", encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if int(data.get("user_id", -1)) != config.user_id:
                        rows.append(line.rstrip("\n"))
        rows.append(json.dumps(config.__dict__, ensure_ascii=False))
        with self._store.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(rows) + "\n")
