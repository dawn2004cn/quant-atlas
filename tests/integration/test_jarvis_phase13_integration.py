import pytest
from unittest.mock import MagicMock, patch
import random

# ---------------------------------------
# MOCK DEPENDENCIES (To make tests isolated)
# Note: These should ideally live in a dedicated test fixture folder.
# ---------------------------------------

class MockDecisionContextDTO:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class MockEvidenceNoteDTO:
    def __init__(self, source, title, payload):
        self.__dict__.update({"source": source, "title": title, "payload": payload})

# ---------------------------------------
# SERVICE MOCKS
# ---------------------------------------

@pytest.fixture(scope="module")
def mock_user_knowledge():
    """Mocks the UserKnowledgeService."""
    return MagicMock()

@pytest.fixture(scope="module")
def mock_clusterer():
    """Mocks ClusterManager for testing router dependency injection."""
    from app.modules.ai_agent.services.archetypes.cluster_manager import ClusterManager
    # Overwrite static method with a controlled mock behavior if needed, 
    # but relying on its stub implementation is fine for now.

@pytest.fixture(scope="module")
def mock_dna_service():
    """Mocks the UserDNAService."""
    from app.modules.ai_agent.services.visualization.user_dna_service import UserDNAService
    return UserDnaservice()

# ---------------------------------------
# SPECIFIC TESTS
# ---------------------------------------

@pytest.fixture(scope="module")
def setup_router(mock_user_knowledge, mock_clusterer, mock_dna_service):
    """Sets up and returns the fully mocked JarvisSemanticRouterService."""
    from app.modules.ai_agent.services.jarvis_semantic_router_service import (
        JarvisSemanticRouterService
    )
    # Mocking internal dependencies of the router itself for simplicity in a test context
    with patch('app.modules.ai_agent.services.jarvis_semantic_router_service._new_decision_id', return_value="mock_uuid"):
        # The actual initialization requires all services to be passed
        return JarvisSemanticRouterService(
            user_knowledge_service=mock_user_knowledge,
            strategy_service=None, # Mocking strategy service for now
            command_plan_service=None,
            cluster_manager=MagicMock(), # Using real stub if possible, or simply passing None/Mocked object.
            user_dna_service=mock_dna_service, 
        )

# Replace the actual test file created previously with a robust integration testing suite.
def test_pattern_matching_integration(setup_router, mock_user_knowledge):
    """
    Tests the primary path: User Query -> Router -> DNA/Persona Enforcement.
    Verifies that winning patterns generate evidence and update the DTO correctly.
    """
    # 1. Setup Mocks for Knowledge Profile (Must contain a wining pattern)
    mock_profile = MagicMock()
    mock_wins = [
        {"sectors": ["Tech"], "factors": ["Momentum"], "symbols": ["600000"]}, # Winning Pattern
        {"sectors": ["Health"], "factors": [], "symbols": []} # Minor pattern
    ]
    mock_profile.get_decision_patterns = mock_wins

    # Set the knowledge service return value
    mock_user_knowledge.get_profile.return_value = mock_profile
    
    # 2. Mock DNA Service Call (We simulate generation success)
    dna_stub = {"winning_buy_ratio": 0.75, "volatility_tolerance": 1.2, "momentum_bias": 0.8}

    with patch.object(setup_router._knowledge.get_profile, return_value=mock_profile):
        # Mock the DNA Service call inside the router's enrichment method (complex patching needed)
        # Due to circular dependencies in service definition, we will test the most outer function:
        
        test_query = "我看了看最近有没有什么科技类的风格的机会？" # Target pattern-matching route
        
        from app.modules.ai_agent.services.jarvis_semantic_router_service import (
             JarvisSemanticRouterService
        )

        # Re-running this ensures we hit the logic paths correctly
        result = setup_router.match_winning_patterns("user123")

        # ASSERTIONS:
        assert result.subject == "winning_patterns:user123"
        # Check if DNA metadata was properly passed into evidence/reasoning
        evidence_sources = [e.source for e in result.evidence]
        assert any("persona_aware" in src for src in evidence_sources)
    
def test_empty_query(setup_router):
    """Tests the base case of an empty user query."""
    test_query = ""
    result = setup_router.route("user456", test_query)
    assert result.input_snapshot.get("ok") is False
    assert "error" in result.input_snapshot

# Add similar minimal tests for _voice_briefing_route and _heuristic_nav to fully verify wiring stability.
