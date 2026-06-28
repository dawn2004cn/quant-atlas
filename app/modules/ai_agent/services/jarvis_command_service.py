from __future__ import annotations

from app.domain.dto.service_result import GenericResponseDTO

"""Quant Jarvis intent parser - converts natural language to system commands."""





import re

from typing import Any



from app.modules.strategy.services.strategy.strategy_service import StrategyApplicationService

from app.modules.strategy.services.analytics.visual_data_reducer_service import VisualDataReducerService

from app.modules.market_data.services.watchlist_risk_service import RiskAlertService




class JarvisIntentParser:

    """Jarvis intent parser - converts natural language to system commands."""



    # Intent pattern mapping

    INTENT_PATTERNS = {

        "find_stocks": [

            r"find.*stock",

            r"recommend.*stock",

            r"find.*stock"
            r"any.*opportunity",

        ],

        "analyze": [

            r"analyze.*\d{6}",

            r"check.*\d{6}",

            r"placeholder"
        ],

        "backtest": [

            r"backtest",

            r"test.*strategy",

        ],

        "risk_alert": [

            r"risk",

            r"alert",

            r"warning",

        ],

        "rebalance": [

            r"rebalance",

            r"position.*suggest",

            r"combine.*optimize",

        ],

        "navigate": [

            r"placeholder"
            r"open.*",

        ],

    }



    # Natural language to filter criteria mapping

    CRITERIA_MAPPING = {

        "cheap": {"pe": {"operator": "<", "value": 15}},

        "undervalued": {"pb": {"operator": "<", "value": 1.5}},

        "high_dividend": {"dividend_yield": {"operator": ">", "value": 3}},

        "high_score": {"score": {"operator": ">", "value": 80}},

        "oversold": {"change_pct": {"operator": "<", "value": -5}},

        "limit_up": {"change_pct": {"operator": ">", "value": 9}},

        "high_volume": {"volume_ratio": {"operator": ">", "value": 2}},

        "small_cap": {"market_cap": {"operator": "<", "value": 50}},

        "large_cap": {"market_cap": {"operator": ">", "value": 500}},

        "st": {"is_st": {"operator": "=", "value": False}},

    }



    @classmethod

    def parse(cls, query: str) -> GenericResponseDTO:

        """Parse user input into intent and parameters."""

        q = query.strip()



        # Detect intent type

        intent = "search"

        for intent_type, patterns in cls.INTENT_PATTERNS.items():

            for pattern in patterns:

                if re.search(pattern, q):

                    intent = intent_type

                    break



        # Extract stock code

        symbol_match = re.search(r"(\d{6})", q)

        symbol = symbol_match.group(1) if symbol_match else None



        # Extract market code

        market = "CN"

        if ".HK" in q.upper():

            market = "HK"

        elif re.search(r"^[A-Z]{1,5}$", q.upper()):

            market = "US"



        # Extract filter criteria

        criteria = cls._extract_criteria(q)



        return {

            "intent": intent,

            "query": q,

            "symbol": symbol,

            "market": market,

            "criteria": criteria,

            "original": q,

        }



    @classmethod

    def _extract_criteria(cls, query: str) -> GenericResponseDTO:

        """Extract filter criteria from natural language."""

        criteria = {"conditions": []}



        for key, value in cls.CRITERIA_MAPPING.items():

            if key in query:

                criteria["conditions"].append(value)



        if criteria["conditions"]:

            criteria["logical_operator"] = "AND"



        return criteria




class JarvisCommandService:

    """Enhanced Jarvis command service - supports intent-driven global interaction."""



    def __init__(

        self,

        strategy_service: StrategyApplicationService | None = None,

        visual_reducer: VisualDataReducerService | None = None,

        risk_alert_service: RiskAlertService | None = None,

        ai_adapter: Any | None = None,

    ):

        self._strategy = strategy_service

        self._visual = visual_reducer

        self._risk = risk_alert_service

        self._ai = ai_adapter

        self._parser = JarvisIntentParser()



    def execute(self, query: str) -> GenericResponseDTO:

        """Execute Jarvis command."""

        parsed = self._parser.parse(query)

        intent = parsed["intent"]



        # Execute different operations based on intent

        if intent == "find_stocks":

            return self._handle_find_stocks(parsed)

        elif intent == "analyze":

            return self._handle_analyze(parsed)

        elif intent == "backtest":

            return self._handle_backtest(parsed)

        elif intent == "risk_alert":

            return self._handle_risk_alert(parsed)

        elif intent == "navigate":

            return self._handle_navigate(parsed)

        else:

            return self._handle_search(parsed)



    def _handle_find_stocks(self, parsed: dict) -> GenericResponseDTO:

        """Handle find stocks request."""

        criteria = parsed.get("criteria", {})

        if criteria.get("conditions"):

            if self._strategy:

                result = self._strategy.custom_criteria_select_stocks(

                    criteria=criteria,

                    market=parsed.get("market", "CN"),

                    top_n=5,

                )

                return {

                    "ok": True,

                    "action": "show_results",

                    "title": "Stocks found based on criteria",

                    "results": result.get("candidates", [])[:5],

                }



        # Default smart stock selection

        if self._strategy:

            result = self._strategy.select_stocks(

                strategy_name="smart",

                market=parsed.get("market", "CN"),

                top_n=5,

            )

            return {

                "ok": True,

                "action": "show_results",

                "title": "Smart stock recommendations",

                "results": result.get("candidates", [])[:5],

            }



        return {"ok": False, "error": "Stock service unavailable"}



    def _handle_analyze(self, parsed: dict) -> GenericResponseDTO:

        """Handle analysis request."""

        symbol = parsed.get("symbol")

        if not symbol:

            return {"ok": False, "error": "Stock code not found"}



        if self._visual:

            result = self._visual.reduce(symbol, parsed.get("market", "CN"))

            return {

                "ok": True,

                "action": "show_analysis",

                "title": f"{symbol} Analysis Report",

                "data": result,

            }



        return {"ok": False, "error": "Analysis service unavailable"}



    def _handle_backtest(self, parsed: dict) -> GenericResponseDTO:

        """Handle backtest request."""

        return {

            "ok": True,

            "action": "navigate",

            "url": "/backtest",

            "title": "Go to backtest lab",

        }



    def _handle_risk_alert(self, parsed: dict) -> GenericResponseDTO:

        """Handle risk alert request."""

        if self._risk:

            return {

                "ok": True,

                "action": "show_risk",

                "title": "Risk alert",

                "description": "Please enter a stock code to perform risk analysis",

            }



        return {"ok": False, "error": "Risk service unavailable"}



    def _handle_navigate(self, parsed: dict) -> GenericResponseDTO:

        """Handle navigation request."""

        query = parsed.get("query", "")



        if "backtest" in query:

            url = "/backtest"

        elif "self-selected" in query:

            url = "/self-stocks"

        elif "factory" in query or "workshop" in query:

            url = "/alpha-factory"

        elif "factor" in query:

            url = "/factor-catalog"

        elif "portfolio" in query or "position" in query:

            url = "/portfolio"

        elif "market" in query:

            url = "/market-panorama"

        else:

            url = "/market-panorama"



        return {

            "ok": True,

            "action": "navigate",

            "url": url,

            "title": f"Navigate to {url}",

        }



    def _handle_search(self, parsed: dict) -> GenericResponseDTO:

        """Handle generic search."""

        return {

            "ok": True,

            "action": "search",

            "url": f"/market-panorama?filter={parsed.get('query', '')}",

            "title": f"Search: {parsed.get('query', '')}",

        }



    def quick_reply(self, query: str) -> str:

        """Quick response for simple queries."""

        q = query.lower()



        # Time related

        if "today" in q and ("recommend" in q or "suggest" in q):

            return "Analyzing today's opportunities, please wait..."



        if "my" in q and "self-selected" in q:

            return "Loading your self-selected stock list..."



        # Analysis request

        if re.search(r"\d{6}", q):

            symbol = re.search(r"\d{6}", q).group()

            return f"Analyzing {symbol}, please wait..."



        return "Processing your request..."




class JarvisGlobalOrchestrator:

    """Jarvis global orchestrator - integrates all services."""



    def __init__(

        self,

        command_service: JarvisCommandService,

        strategy_service: StrategyApplicationService | None = None,

    ):

        self._command = command_service

        self._strategy = strategy_service



    def process(self, user_input: str) -> GenericResponseDTO:

        """Process user input and return results."""

        # Quick analysis

        parsed = self._parser.parse(user_input)



        # If there are clear filter criteria, use custom_criteria

        if parsed.get("criteria", {}).get("conditions") and self._strategy:

            criteria = parsed["criteria"]

            market = parsed.get("market", "CN")



            result = self._strategy.custom_criteria_select_stocks(

                criteria=criteria,

                market=market,

                top_n=5,

            )



            return {

                "ok": True,

                "type": "stock_results",

                "data": result,

                "friendly_message": self._translate_criteria_to_message(criteria),

            }



        # Otherwise use standard command service

        return self._command.execute(user_input)



    def _translate_criteria_to_message(self, criteria: dict) -> str:

        """Translate filter criteria to user-friendly message."""

        conditions = criteria.get("conditions", [])

        if not conditions:

            return "Found the following stocks for you?"



        parts = []

        for c in conditions:

            if "pe" in c:

                parts.append("Low PE")

            if "pb" in c:

                parts.append("Low PB")

            if "dividend_yield" in c:

                parts.append("High dividends")

            if "change_pct" in c:

                op = c.get("change_pct", {}).get("operator", ">")

                if op == "<":

                    parts.append("oversold")

                else:

                    parts.append("Strong gains")

            if "volume_ratio" in c:

                parts.append("high_volume")



        return f"Stocks filtered by {' '.join(parts)} for you: " if parts else "Found the following stocks for you: "
