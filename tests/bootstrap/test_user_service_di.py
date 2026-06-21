import pytest
from unittest.mock import Mock
from app.application.services.user_service import UserApplicationService
from app.domain.ports.repository_ports import UserRepository
from app.core.container import Container

@pytest.fixture
def user_service():
    # Setup Container with mocked repository
    container = Container()
    mock_repo = Mock(spec=UserRepository)
    
    # Inject the mock into the container
    container.user_repository.override(mock_repo)
    
    # Return the service from the container
    return container.user_service(), mock_repo

def test_list_users_calls_repository(user_service):
    service, mock_repo = user_service
    
    # Configure mock
    mock_repo.list_users.return_value = []
    
    # Execute
    result = service.list_users()
    
    # Verify
    assert result == []
    mock_repo.list_users.assert_called_once()
