import os
import pytest
from unittest.mock import MagicMock, patch
from squeeze.report.notifier import LineNotifier

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("LINE_USER_ID", "test_user")

def test_line_notifier_init_from_env(mock_env):
    notifier = LineNotifier()
    assert notifier.access_token == "test_token"
    assert notifier.user_id == "test_user"

def test_line_notifier_init_explicit():
    notifier = LineNotifier(access_token="explicit_token", user_id="explicit_user")
    assert notifier.access_token == "explicit_token"
    assert notifier.user_id == "explicit_user"

@patch('squeeze.report.notifier.MessagingApi')
@patch('squeeze.report.notifier.ApiClient')
@patch('squeeze.report.notifier.Configuration')
def test_send_summary_success(mock_config, mock_api_client, mock_messaging_api, mock_env):
    # Setup mocks
    mock_instance = mock_messaging_api.return_value
    
    notifier = LineNotifier()
    result = notifier.send_summary("Test message")
    
    assert result is True
    mock_messaging_api.assert_called_once()
    mock_instance.push_message.assert_called_once()

def test_send_summary_missing_config():
    with patch.dict(os.environ, {}, clear=True):
        notifier = LineNotifier()
        result = notifier.send_summary("Test message")
        assert result is False

def test_send_summary_empty_message(mock_env):
    notifier = LineNotifier()
    result = notifier.send_summary("")
    assert result is False
