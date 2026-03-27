import pytest
import requests
from squeeze.core.session import get_robust_session, robust_request, HTTPError
from unittest.mock import MagicMock, patch

def test_get_robust_session_headers():
    session = get_robust_session()
    assert "User-Agent" in session.headers
    assert "Mozilla/5.0" in session.headers["User-Agent"]

@patch("requests.Session.request")
def test_robust_request_success(mock_request):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_request.return_value = mock_response
    
    response = robust_request("GET", "https://example.com")
    assert response.status_code == 200
    assert mock_request.call_count == 1

@patch("requests.Session.request")
def test_robust_request_retry_on_429(mock_request):
    # Setup mock to fail once with 429 then succeed
    fail_response = MagicMock()
    fail_response.status_code = 429
    fail_response.reason = "Too Many Requests"
    
    success_response = MagicMock()
    success_response.status_code = 200
    
    mock_request.side_effect = [fail_response, success_response]
    
    # We need to speed up the test by reducing wait time
    with patch("squeeze.core.session.wait_exponential_jitter", return_value=lambda x: 0):
        response = robust_request("GET", "https://example.com")
        assert response.status_code == 200
        assert mock_request.call_count == 2

@patch("requests.Session.request")
def test_robust_request_fail_after_max_attempts(mock_request):
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.reason = "Internal Server Error"
    mock_request.return_value = fail_response
    
    with patch("squeeze.core.session.wait_exponential_jitter", return_value=lambda x: 0):
        with pytest.raises(Exception): # tenacity raises RetryError or the last exception
            robust_request("GET", "https://example.com")
    
    # It should have tried 5 times
    assert mock_request.call_count == 5
