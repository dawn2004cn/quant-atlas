from abc import ABC, abstractmethod
from typing import Any, dict


class CommandPlanServiceABC(ABC):
    """
    Abstract Base Class for translating vague natural language commands
    into structured sequences of actionable steps (a 'playbook').

    This defines the contract that any concrete AI planning module must follow.
    It translates intent into a structured decision context ready for routing.
    """

    @abstractmethod
    def build_semantic_plan(self, text: str, user_id: str | int | None) -> dict[str, Any]:
        """
        Analyzes the input text to assign an optimal command intent and
        gather initial supporting parameters. Must return a structured dictionary plan.
        Example structure: {"intent": "...", "label": "...", "url": "/path", "params": {...}}
        """
        raise NotImplementedError("Must be implemented by concrete class.")

    @abstractmethod
    def refine_plan(self, initial_plan: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """
        Allows the central router to feed back contextual information (e.g., current market state)
        to refine or modify a previously generated plan/intent structure.
        """
        raise NotImplementedError("Must be implemented by concrete class.")
