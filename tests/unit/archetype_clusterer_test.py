import pytest
from app.modules.ai_agent.services.archetypes.cluster_manager import ClusterManager

def test_generate_winning_archetype():
    # Test with mock historical data simulating both wins and losses.
    mock_history = [
        {"timestamp": 1, "action": "buy", "asset": "tech_a", "outcome": 0.8}, # Simulate positive outcome
        {"timestamp": 2, "action": "sell", "asset": "energy_b", "outcome": 0.3}
    ]
    # Expect an array of descriptive strings (The Archetype DNA) and ensure at least one is returned.
    archetypes = ClusterManager.find_winning_archetypes(mock_history)
    assert isinstance(archetypes, list)
    if mock_history:
        assert len(archetypes) > 0

def test_generate_no_archetype():
    # Test case for empty history input
    empty_history = []
    archetypes = ClusterManager.find_winning_archetypes(empty_history)
    assert archetypes == []