import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from squeeze.report.notifier import LineNotifier, EmailNotifier

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

@patch("squeeze.report.notifier.smtplib.SMTP")
def test_email_notifier_attaches_png_as_attachment(mock_smtp, tmp_path, monkeypatch):
    monkeypatch.setenv("SMTP_USERNAME", "user@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_RECIPIENT", "dest@example.com")

    png_path = tmp_path / "chart.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    notifier = EmailNotifier()
    assert notifier.send_email("subject", "<b>body</b>", is_html=True, attachments=[png_path]) is True

    smtp_instance = mock_smtp.return_value
    sent_message = smtp_instance.sendmail.call_args[0][2]
    assert 'filename="chart.png"' in sent_message
    assert "Content-Disposition: attachment;" in sent_message
