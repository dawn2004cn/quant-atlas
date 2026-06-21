from __future__ import annotations
"""AI and agent ports."""


from abc import ABC, abstractmethod
from typing import Any


class KronosRepository(ABC):
    """Port for Kronos ML model persistence."""

    @abstractmethod
    def save_model(self, model: Any) -> str:
        """Save Kronos model."""
        raise NotImplementedError

    @abstractmethod
    def get_model(self, model_id: str) -> Any | None:
        """Get Kronos model."""
        raise NotImplementedError

    @abstractmethod
    def list_models(self) -> list[dict[str, Any]]:
        """List available models."""
        raise NotImplementedError


class KronosPredictorPort(ABC):
    """Port for Kronos prediction service."""

    @abstractmethod
    def predict(self, symbol: str, horizon: int = 20) -> dict[str, Any]:
        """Run prediction."""
        raise NotImplementedError

    @abstractmethod
    def batch_predict(self, symbols: list[str], horizon: int = 20) -> list[dict[str, Any]]:
        """Run batch prediction."""
        raise NotImplementedError


class OpenBBRepository(ABC):
    """Port for OpenBB data persistence."""

    @abstractmethod
    def save_data(self, key: str, data: Any) -> bool:
        """Save data to cache."""
        raise NotImplementedError

    @abstractmethod
    def get_data(self, key: str) -> Any | None:
        """Get cached data."""
        raise NotImplementedError


class QuantMLFactorRepository(ABC):
    """Port for QuantML factor storage."""

    @abstractmethod
    def save_factor(self, factor: Any) -> str:
        """Save factor definition."""
        raise NotImplementedError

    @abstractmethod
    def get_factor(self, factor_id: str) -> Any | None:
        """Get factor definition."""
        raise NotImplementedError

    @abstractmethod
    def list_factors(self) -> list[dict[str, Any]]:
        """List all factors."""
        raise NotImplementedError


class AgentRepository(ABC):
    """Port for AI agent state persistence."""

    @abstractmethod
    def save_state(self, agent_id: str, state: dict[str, Any]) -> bool:
        """Save agent state."""
        raise NotImplementedError

    @abstractmethod
    def get_state(self, agent_id: str) -> dict[str, Any] | None:
        """Get agent state."""
        raise NotImplementedError

    @abstractmethod
    def save_market_insight(self, insight: MarketInsight) -> int:
        """Save market insight."""
        raise NotImplementedError

    @abstractmethod
    def list_market_insights(self, market: str, limit: int = 10) -> list[MarketInsight]:
        """List market insights."""
        raise NotImplementedError

    @abstractmethod
    def save_report_interpretation(self, interpretation: ReportInterpretation) -> int:
        """Save report interpretation."""
        raise NotImplementedError


class AgentPort(ABC):
    """Base protocol for all AI agents in the unified platform.

    Every agent implementation must provide ``agent_name`` and ``agent_type``
    attributes and implement ``invoke()`` with the standardized signature.
    """

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable agent name (e.g. 'trading_research')."""

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Agent category: 'research', 'swarm', 'autonomous', 'hedge_fund', etc."""

    @abstractmethod
    async def invoke(
        self,
        inputs: dict[str, Any],
        user_id: int = 0,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute the agent with given inputs.

        Returns dict with at least ``ok`` key; additional keys are
        forwarded to the caller.
        """


class AgentLLMPort(ABC):
    """Port for LLM integration in agents."""

    @abstractmethod
    def generate(self, prompt: str, params: dict[str, Any] | None = None) -> str:
        """Generate text from LLM."""
        raise NotImplementedError

    @abstractmethod
    def chat(self, messages: list[dict[str, str]], params: dict[str, Any] | None = None) -> str:
        """Chat with LLM."""
        raise NotImplementedError


class SwarmOrchestratorPort(ABC):
    """Port for running multi-agent swarms."""

    @abstractmethod
    def run_swarm(
        self,
        preset_name: str,
        topic: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a swarm preset with a given topic."""
        raise NotImplementedError

    @abstractmethod
    def list_presets(self) -> list[str]:
        """List available swarm presets."""
        raise NotImplementedError

    @abstractmethod
    def get_run_status(self, run_id: str) -> dict[str, Any] | None:
        """Get the status of a specific swarm run."""
        raise NotImplementedError


class ExpertSkillPort(ABC):
    """Port for accessing specialized financial expert skills."""

    @abstractmethod
    def load_skill(
        self,
        skill_name: str,
    ) -> dict[str, Any]:
        """Load a specific skill by name."""
        raise NotImplementedError

    @abstractmethod
    def list_skills(self) -> list[str]:
        """List available skills."""
        raise NotImplementedError


class ToolFacadePort(ABC):
    """Port for Agent tool facades - provides tool-friendly entrypoints over application services."""

    @abstractmethod
    def fetch_bars(
        self,
        symbol: str,
        market: Any,
        *,
        period: str = "1y",
        interval: str = "1d",
    ) -> tuple[list[dict[str, Any]], str]:
        """Return (bars, evidence_note)."""
        raise NotImplementedError

    @abstractmethod
    def fetch_profile(self, symbol: str, market: Any) -> tuple[dict | None, str]:
        """Lightweight profile probe for ticker validation."""
        raise NotImplementedError

    @abstractmethod
    def cn_financial_bundle(self, symbol: str) -> dict[str, Any]:
        """Return financial bundle for symbol."""
        raise NotImplementedError

    @abstractmethod
    def cn_research_reports(
        self, symbol: str, limit: int = 30
    ) -> tuple[list[dict[str, Any]], str | None]:
        """Return research reports for symbol."""
        raise NotImplementedError

    @abstractmethod
    def news_bundle(
        self,
        symbol: str,
        market: Any,
        *,
        force_refresh: bool = False,
        cache_max_age_hours: float = 24.0,
    ) -> dict[str, Any]:
        """Return bundled news with archive."""
        raise NotImplementedError

    @abstractmethod
    def run_backtest(
        self,
        *,
        strategy_name: str,
        ticker: str,
        market: Any,
        params: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        """Run backtest and return (result, note)."""
        raise NotImplementedError

    @abstractmethod
    def run_selector(
        self,
        *,
        model_name: str,
        market: Any,
        criteria: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        """Run stock selection and return (result, note)."""
        raise NotImplementedError


class QlibDataProviderPort(ABC):
    """Port for Qlib data adapter - provides normalized bar data for Qlib pipelines."""

    @abstractmethod
    def fetch_daily_bars(
        self,
        symbol: str,
        market: Any,
        *,
        period: str = "2y",
    ) -> tuple[list[dict[str, Any]], str]:
        """Return normalized OHLCV bars with string dates (YYYY-MM-DD)."""
        raise NotImplementedError

    @abstractmethod
    def bars_to_dataframe(self, bars: list[dict[str, Any]]):
        """Convert normalized bars to pandas DataFrame."""
        raise NotImplementedError

    @abstractmethod
    def status(self) -> dict[str, Any]:
        """Return Qlib pipeline status."""
        raise NotImplementedError

    @abstractmethod
    def unified_buy_hold_backtest(
        self,
        symbol: str,
        market: Any,
        *,
        start: str,
        end: str,
    ) -> dict[str, Any]:
        """Run unified buy-and-hold backtest."""
        raise NotImplementedError