import pytest

from app.core.services.stub_concrete_user_knowledge_service import ConcreteUserKnowledgeService


@pytest.fixture
def user_knowledge_service(tmp_path) -> ConcreteUserKnowledgeService:
    return ConcreteUserKnowledgeService(store_path=tmp_path / "user_knowledge.json")


def test_get_profile_empty_user(user_knowledge_service: ConcreteUserKnowledgeService) -> None:
    profile = user_knowledge_service.get_profile(1234567890)
    assert profile["user_id"] == "1234567890"
    assert profile["total_decisions"] == 0
    assert isinstance(profile["decision_patterns"], list)


def test_get_profile_string_user_id(user_knowledge_service: ConcreteUserKnowledgeService) -> None:
    profile = user_knowledge_service.get_profile("agent_b3f")
    assert profile["user_id"] == "agent_b3f"


def test_get_pattern_not_found(user_knowledge_service: ConcreteUserKnowledgeService) -> None:
    assert user_knowledge_service.get_pattern("123", "missing_quantum_concept") is None


def test_record_decision_creates_patterns(user_knowledge_service: ConcreteUserKnowledgeService) -> None:
    user_knowledge_service.record_decision(42, symbol="600519", action="buy")
    user_knowledge_service.record_decision(42, symbol="600519", action="sell")
    patterns = user_knowledge_service.get_all_patterns(42, outcome=("win", "profit"))
    assert len(patterns) >= 1
