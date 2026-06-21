from abc import ABC, abstractmethod
from typing import Any, List, Optional
from app.domain.dto.decision_context_dto import EvidenceNoteDTO


class UserKnowledgeServiceABC(ABC):
    """
    Abstract Base Class for retrieving and interpreting user's historical 
    knowledge patterns (e.g., winning trades, investment habits).

    This defines the contract that any concrete implementation must follow.
    """

    @abstractmethod
    def get_profile(self, user_id: str | int) -> dict[str, Any]:
        """
        Retrieves a comprehensive dictionary profile for a given user ID. 
        This structure should contain historical metrics and defined patterns.
        """
        raise NotImplementedError("Must be implemented by concrete class.")

    @abstractmethod
    def get_pattern(self, user_id: str | int, pattern_type: str) -> Optional[dict]:
        """
        Retrieves a specific type of saved recurring pattern for the user.
        Returns None if no such pattern is found.
        """
        raise NotImplementedError("Must be implemented by concrete class.")

    # Future expansion: methods for integrating with external pattern engines 
