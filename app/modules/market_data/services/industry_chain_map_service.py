from __future__ import annotations
from app.domain.dto.service_result import GenericResponseDTO
"""Industry Chain Map - 产业链机会地图服务."""



from app.core.registry import register_service
from app.domain.enums import MarketCode
from app.domain.ports import MarketDataProvider


# 产业链映射配置
INDUSTRY_CHAIN_CONFIG = {
    "AI": {
        "name": "人工智能",
        "upstream": ["光模块", "芯片", "算力", "服务器", "PCB"],
        "downstream": ["大模型", "应用", "智能驾驶", "机器人"],
        "related": ["600522", "002185", "000938", "002408", "300308"],
    },
    "新能源汽车": {
        "name": "新能源汽车",
        "upstream": ["锂电池", "锂矿", "碳酸锂", "正极", "负极", "电解液"],
        "downstream": ["整车", "充电桩", "换电站"],
        "related": ["002594", "300750", "002466", "002460", "002812"],
    },
    "光伏": {
        "name": "光伏",
        "upstream": ["硅料", "硅片", "EVA胶膜"],
        "downstream": ["组件", "逆变器", "支架"],
        "related": ["600438", "002129", "002006", "002309"],
    },
    "半导体": {
        "name": "半导体",
        "upstream": ["硅片", "光刻机", "特种气体"],
        "downstream": ["芯片设计", "封测", "晶圆制造"],
        "related": ["688981", "688396", "688008", "603986"],
    },
    "医药": {
        "name": "医药",
        "upstream": ["原料药", "中间体"],
        "downstream": ["中药", "疫苗", "医疗器械"],
        "related": ["600518", "000566", "300003", "002007"],
    },
    "银行": {
        "name": "银行",
        "upstream": [],
        "downstream": [],
        "related": ["601398", "601939", "601288", "600036"],
    },
}


class IndustryChainAnalyzer:
    """产业链分析器."""

    @classmethod
    def get_upstream(cls, industry: str) -> list[str]:
        """获取上游产业."""
        config = INDUSTRY_CHAIN_CONFIG.get(industry, {})
        return config.get("upstream", [])

    @classmethod
    def get_downstream(cls, industry: str) -> list[str]:
        """获取下游产业."""
        config = INDUSTRY_CHAIN_CONFIG.get(industry, {})
        return config.get("downstream", [])

    @classmethod
    def find_related_symbols(cls, industry: str) -> list[str]:
        """获取关联股票."""
        config = INDUSTRY_CHAIN_CONFIG.get(industry, {})
        return config.get("related", [])


class ChainEffectCalculator:
    """联动效应计算器."""

    @staticmethod
    def calculate_price_impact(
        source_symbol: str,
        source_change_pct: float,
        related_symbols: list[str],
        market_provider: MarketDataProvider | None = None,
    ) -> GenericResponseDTO:
        """计算价格联动影响."""
        if not market_provider or abs(source_change_pct) < 1:
            return {"ok": False, "error": "数据不足"}

        impacts = []
        for sym in related_symbols[:10]:
            try:
                profile = market_provider.get_stock_profile(sym, MarketCode.CN)
                if profile:
                    price = float(profile.get("price", 0) or 0)
                    change = float(profile.get("change_pct", 0) or 0)
                    # 简单的相关性计算
                    correlation = min(abs(source_change_pct * 0.3), abs(change)) if change else 0

                    impacts.append({
                        "symbol": sym,
                        "name": profile.get("name", sym),
                        "price": price,
                        "change_pct": round(change, 2),
                        "correlation": round(correlation, 2),
                        "effect": "positive" if change * source_change_pct > 0 else "negative",
                    })
            except Exception:
                continue

        impacts.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)

        return {
            "ok": True,
            "source": source_symbol,
            "source_change": source_change_pct,
            "affected_stocks": impacts,
        }


class MaterialImpactAnalyzer:
    """原材料价格影响分析器."""

    MATERIAL_STOCKS = {
        "碳酸锂": ["002466", "002460", "002708"],
        "硅料": ["600438", "002129"],
        "原油": ["600857", "601857"],
        "铜": ["601898", "600362"],
        "铝": ["600600", "000807"],
    }

    @classmethod
    def analyze_price_change(
        cls,
        material: str,
        price_change_pct: float,
        watchlist_symbols: list[str],
    ) -> GenericResponseDTO:
        """分析原材料价格变化对持仓的影响."""
        material_stocks = cls.MATERIAL_STOCKS.get(material, [])

        beneficiaries = []
        victims = []

        # 简单逻辑：原材料涨利好上游，利空下游
        if material in ["碳酸锂", "硅料", "原油", "铜", "铝"]:
            if price_change_pct > 0:
                beneficiaries = [s for s in material_stocks if s in watchlist_symbols]
            else:
                victims = [s for s in material_stocks if s in watchlist_symbols]

        return {
            "material": material,
            "price_change": price_change_pct,
            "beneficiaries": beneficiaries,
            "victims": victims,
            "impact_assessment": "positive" if price_change_pct > 0 else "negative",
        }


@register_service(name="industry_chain_service")
class IndustryChainMapService:
    """产业链地图服务."""

    def __init__(
        self,
        market_provider: MarketDataProvider | None = None,
    ):
        self._market = market_provider

    def build_chain(
        self,
        *,
        symbol: str,
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """Alias for HTTP/diagnosis callers (same payload as ``get_chain_map``)."""
        return self.get_chain_map(symbol, market)

    def get_chain_map(
        self,
        symbol: str,
        market: MarketCode = MarketCode.CN,
    ) -> GenericResponseDTO:
        """获取个股的产业链拓扑图."""
        # 先获取股票的行业信息
        profile = self._market.get_stock_profile(symbol, market) if self._market else {}
        industry = profile.get("industry", "")

        # 找到相关产业链
        chain = None
        for key, config in INDUSTRY_CHAIN_CONFIG.items():
            if key in industry or any(k in industry for k in [key, config.get("name", "")]):
                chain = key
                break

        if not chain:
            # 尝试通过关联股票反推
            for key, config in INDUSTRY_CHAIN_CONFIG.items():
                related = config.get("related", [])
                if symbol in related:
                    chain = key
                    break

        if not chain:
            return {
                "ok": False,
                "error": "未找到相关产业链",
            }

        config = INDUSTRY_CHAIN_CONFIG[chain]
        related_symbols = config.get("related", [])

        # 计算联动效应
        source_change = float(profile.get("change_pct", 0) or 0) if profile else 0
        effects = ChainEffectCalculator.calculate_price_impact(
            symbol, source_change, related_symbols, self._market
        )
        effects.pop("ok", None)

        return {
            "ok": True,
            "chain": chain,
            "chain_name": config.get("name", ""),
            "upstream": config.get("upstream", []),
            "downstream": config.get("downstream", []),
            "related_symbols": related_symbols,
            "chain_effects": effects,
            "visualization": self._generate_mermaid(industry=chain, related=related_symbols),
        }

    def get_watchlist_chain_analysis(
        self,
        symbols: list[str],
    ) -> GenericResponseDTO:
        """分析自选股的产业链分布."""
        industry_map = {}
        concentration = []

        for symbol in symbols:
            if not self._market:
                continue
            profile = self._market.get_stock_profile(symbol, MarketCode.CN)
            if not profile:
                continue

            industry = profile.get("industry", "未分类")
            if industry not in industry_map:
                industry_map[industry] = []
            industry_map[industry].append({
                "symbol": symbol,
                "name": profile.get("name", symbol),
                "change_pct": profile.get("change_pct", 0),
            })

        # 计算集中度
        for ind, stocks in industry_map.items():
            concentration.append({
                "industry": ind,
                "count": len(stocks),
                "percentage": round(len(stocks) / len(symbols) * 100, 1),
            })

        concentration.sort(key=lambda x: x["count"], reverse=True)

        return {
            "ok": True,
            "industry_distribution": industry_map,
            "concentration": concentration,
            "risk_warning": self._check_concentration_risk(concentration),
        }

    def _check_concentration_risk(self, concentration: list[dict]) -> str | None:
        """检查行业集中度风险."""
        if not concentration:
            return None

        top = concentration[0]
        if top.get("percentage", 0) > 50:
            return f"您的自选股过于集中在 {top['industry']} 行业，建议分散投资以降低风险。"

        return None

    def _generate_mermaid(
        self,
        industry: str,
        related: list[str],
    ) -> str:
        """生成 Mermaid 流程图."""
        config = INDUSTRY_CHAIN_CONFIG.get(industry, {})
        upstream = config.get("upstream", [])
        downstream = config.get("downstream", [])

        lines = ["graph TD"]
        lines.append(f"    {industry}[{config.get('name', industry)}]")

        for i, u in enumerate(upstream[:3]):
            lines.append(f"    U{i}[{u}] --> {industry}")

        for i, d in enumerate(downstream[:3]):
            lines.append(f"    {industry} --> D{i}[{d}]")

        return "\n".join(lines)
