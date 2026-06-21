from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Smart Daily Briefing - 智能投研日报服务."""


from datetime import datetime
from typing import Any

from app.core.logger import get_logger
from app.domain.enums import MarketCode
from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService

logger = get_logger(__name__)


class StrategyTranslator:
    """策略翻译层：将技术术语翻译为用户易懂的大白话。"""

    STRATEGY_DESCRIPTIONS = {
        "mean_reversion": "超跌反弹机会",
        "momentum": "强势追涨标的",
        "value": "低估值价值股",
        "growth": "高成长潜力股",
        "category:trend_following": "趋势追踪型",
        "category:breakout": "突破新高型",
        "category:reversal": "反转抄底型",
        "category:earnings": "业绩驱动型",
        "category:sentiment": "市场情绪型",
    }

    CATEGORY_LABELS = {
        "trend_following": "趋势投资",
        "breakout": "突破投资",
        "reversal": "反转投资",
        "earnings": "价值投资",
        "sentiment": "题材投资",
    }

    @classmethod
    def translate_strategy(cls, strategy: str) -> str:
        """将策略名翻译为用户易懂的语言."""
        s = strategy.lower()
        if s in cls.STRATEGY_DESCRIPTIONS:
            return cls.STRATEGY_DESCRIPTIONS[s]
        for key, desc in cls.STRATEGY_DESCRIPTIONS.items():
            if key in s:
                return desc
        return strategy

    @classmethod
    def translate_reason(cls, reason_code: str) -> str:
        """将技术指标原因翻译为理由."""
        translators = {
            "rsi_oversold": "RSI指标处于超卖区域，存在反弹机会",
            "rsi_overbought": "RSI指标处于超买区域，注意回调风险",
            "price_above_ma20": "价格站上20日均线，短期趋势向上",
            "price_below_ma20": "价格跌破20日均线，短期趋势向下",
            "golden_cross": "出现金叉信号，买入信号",
            "death_cross": "出现死叉信号，卖出信号",
            "volume_surge": "成交量突增，市场关注度提升",
            "sentiment_positive": "舆情偏正面，市场情绪乐观",
            "sentiment_negative": "舆情偏负面，市场情绪悲观",
            "pe_low": "估值处于历史低位",
            "pe_high": "估值处于历史高位",
            "growth_high": "业绩增长强劲",
            "dividend_yield": "股息率较高，收益稳定",
        }
        return translators.get(reason_code.lower(), reason_code)

    @classmethod
    def get_category_label(cls, category: str) -> str:
        """获取分类的中文标签."""
        return cls.CATEGORY_LABELS.get(category.lower(), category)


class SmartDailyBriefingService:
    """智能投研日报服务 - 一键体检 + 叙事合成."""

    def __init__(
        self,
        strategy_service: StrategyApplicationService,
        sentiment_provider: Any | None = None,
        *,
        narrative_synthesis_service: Any | None = None,
        user_knowledge_service: Any | None = None,
        user_decision_context_service: Any | None = None,
    ) -> None:
        self._strategy_service = strategy_service
        self._sentiment_provider = sentiment_provider
        self._narrative = narrative_synthesis_service
        self._knowledge = user_knowledge_service
        self._decision_ctx = user_decision_context_service

    def generate_briefing(
        self,
        market: MarketCode = MarketCode.CN,
        top_n: int = 3,
        *,
        user_id: str | int | None = None,
        role: str | None = None,
        investment_profile: dict[str, Any] | None = None,
        use_narrative: bool = True,
    ) -> GenericResponseDTO:
        """
        生成智能投研日报 - 一键体检核心入口.
        
        流程: 筛选 -> 情绪过滤 -> 模拟回测 -> 返回最优N只
        """
        # 1. 智能选股 (自动根据市场环境选择策略)
        selection_result = self._strategy_service.select_stocks(
            strategy_name="smart",
            market=market,
            top_n=top_n * 4,  # 预留过滤空间
        )

        if not selection_result.get("ok"):
            return {
                "ok": False,
                "error": selection_result.get("error", "选股失败"),
                "briefing_date": datetime.now().strftime("%Y-%m-%d"),
            }

        # 2. 获取候选股票
        candidates = selection_result.get("candidates", [])
        if not candidates:
            return {
                "ok": False,
                "error": "未找到符合条件的股票",
                "briefing_date": datetime.now().strftime("%Y-%m-%d"),
            }

        # 3. 情绪过滤 (如果可用)
        filtered = candidates
        if self._sentiment_provider:
            filtered = self._filter_by_sentiment(candidates)

        # 4. 生成推荐结果
        final_stocks = filtered[:top_n]
        recommendations = []
        
        for stock in final_stocks:
            rec = self._generate_recommendation(stock, selection_result)
            recommendations.append(rec)

        # 5. 市场环境分析
        market_analysis = self._analyze_market_environment(selection_result)

        payload: dict[str, Any] = {
            "ok": True,
            "briefing_date": datetime.now().strftime("%Y-%m-%d"),
            "market": market.value,
            "total_scanned": len(candidates),
            "filtered_count": len(filtered),
            "market_environment": market_analysis,
            "recommendations": recommendations,
            "summary": self._generate_summary(recommendations),
            "narrative_mode": "structured",
        }

        uid = user_id if user_id is not None else "anonymous"
        if use_narrative and self._narrative is not None and uid != "anonymous":
            try:
                profile = investment_profile
                if profile is None and self._knowledge is not None:
                    profile = self._knowledge.get_profile(uid)
                narrative = self._narrative.synthesize_daily_briefing(
                    user_id=uid,
                    briefing=payload,
                    investment_profile=profile if isinstance(profile, dict) else None,
                    role=role,
                )
                payload["narrative"] = narrative
                payload["narrative_mode"] = narrative.get("mode", "template")
                if narrative.get("causal_report"):
                    payload["causal_report"] = narrative["causal_report"]
                if narrative.get("opening"):
                    payload["summary"] = narrative.get("personalized_closing") or payload["summary"]
                for rec in payload["recommendations"]:
                    sym = str(rec.get("symbol") or "")
                    match = next(
                        (
                            n
                            for n in (narrative.get("recommendation_narratives") or [])
                            if str(n.get("symbol")) == sym
                        ),
                        None,
                    )
                    if match and match.get("narrative"):
                        rec["narrative"] = match["narrative"]
            except Exception as exc:
                logger.warning("smart_briefing narrative synthesis failed: %s", exc)
                payload["narrative_mode"] = "structured"

        return payload

    def _filter_by_sentiment(self, stocks: list[dict]) -> list[dict]:
        """基于舆情过滤股票."""
        if not self._sentiment_provider:
            return stocks

        filtered = []
        for stock in stocks:
            symbol = stock.get("symbol", "")
            try:
                sentiment = self._sentiment_provider.get_sentiment(symbol)
                if sentiment and sentiment.get("score", 0.5) > 0.4:
                    stock["sentiment_score"] = sentiment.get("score", 0.5)
                    filtered.append(stock)
            except Exception:
                filtered.append(stock)

        return filtered

    def _generate_recommendation(
        self,
        stock: dict,
        selection_result: dict,
    ) -> GenericResponseDTO:
        """为单只股票生成推荐理由."""
        symbol = stock.get("symbol", "")
        name = stock.get("name", symbol)
        
        # 策略翻译
        strategy = selection_result.get("effective_strategy_group", "unknown")
        strategy_desc = StrategyTranslator.translate_strategy(strategy)
        
        # 构建理由
        reasons = []
        
        # 基于价格变化
        change_pct = abs(stock.get("change_pct", 0))
        if change_pct > 5:
            if stock.get("change_pct", 0) > 0:
                reasons.append(f"今日涨幅{change_pct:.1f}%，表现强势")
            else:
                reasons.append(f"今日跌幅{change_pct:.1f}%，存在超跌反弹机会")
        
        # 基于技术指标
        if stock.get("rsi", 50) < 30:
            reasons.append("RSI超卖，反弹潜力大")
        elif stock.get("rsi", 50) > 70:
            reasons.append("RSI超买，注意回调风险")
        
        # 基于成交量
        if stock.get("volume_ratio", 1) > 2:
            reasons.append("成交量放大，关注度提升")
        
        # 基于舆情
        sentiment = stock.get("sentiment_score")
        if sentiment:
            if sentiment > 0.6:
                reasons.append("舆情偏正面")
            elif sentiment < 0.4:
                reasons.append("舆情偏负面")

        return {
            "symbol": symbol,
            "name": name,
            "price": stock.get("price", 0),
            "change_pct": stock.get("change_pct", 0),
            "strategy_type": strategy_desc,
            "reasons": reasons[:3],  # 最多3条理由
            "confidence": self._calculate_confidence(stock),
        }

    def _calculate_confidence(self, stock: dict) -> float:
        """计算推荐置信度."""
        score = 0.5
        
        # 涨幅因素
        change = abs(stock.get("change_pct", 0))
        if 3 < change < 8:
            score += 0.1
        
        # RSI因素
        rsi = stock.get("rsi", 50)
        if 25 < rsi < 35 or 65 < rsi < 75:
            score += 0.15
        
        # 成交量因素
        if stock.get("volume_ratio", 1) > 1.5:
            score += 0.1
        
        # 舆情因素
        if stock.get("sentiment_score"):
            score += stock.get("sentiment_score", 0.5) * 0.15
        
        return min(round(score, 2), 1.0)

    def _analyze_market_environment(self, selection_result: dict) -> GenericResponseDTO:
        """分析市场环境."""
        sentiment = selection_result.get("sentiment_analysis", {})
        regime = sentiment.get("market_regime", "unknown")
        categories = sentiment.get("recommended_categories", [])
        
        # 翻译分类
        category_labels = [
            StrategyTranslator.get_category_label(c) for c in categories
        ]
        
        env_descriptions = {
            "bull": "牛市环境，建议趋势追踪",
            "bear": "熊市环境，注意防守",
            "sideways": "震荡市，适合高抛低吸",
            "volatile": "高波动市，注意风险",
        }
        
        return {
            "regime": regime,
            "regime_description": env_descriptions.get(regime, regime),
            "recommended_strategies": category_labels,
        }

    def _generate_summary(self, recommendations: list[dict]) -> str:
        """生成日报摘要."""
        if not recommendations:
            return "今日暂无推荐"
        
        count = len(recommendations)
        symbols = [r.get("symbol", "") for r in recommendations]
        
        return f"今日为您精选{count}只标的：{', '.join(symbols)}。点击查看详细分析。"