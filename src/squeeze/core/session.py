import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception,
)
import logging

logger = logging.getLogger(__name__)

# Constants
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

class HTTPError(Exception):
    """Custom exception for HTTP errors to be handled by tenacity."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP {status_code}: {message}")

def is_retryable_error(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry."""
    if isinstance(exception, HTTPError):
        # Retry on 429 (Too Many Requests) or 5xx (Server errors)
        return exception.status_code == 429 or 500 <= exception.status_code < 600
    if isinstance(exception, (requests.exceptions.RequestException)):
        # Retry on common network issues
        return True
    return False

def get_robust_session() -> requests.Session:
    """
    Returns a requests session with custom User-Agent.
    Note: yfinance currently has issues with requests-cache and curl_cffi.
    """
    session = requests.Session()
    
    session.headers.update({
        "User-Agent": USER_AGENT,
    })
    
    return session

def robust_request(method, url, session=None, **kwargs):
    """
    Wrapper for requests that includes retry logic for 429 and 5xx errors.
    """
    if session is None:
        session = get_robust_session()
        
    @retry(
        retry=retry_if_exception(is_retryable_error),
        wait=wait_exponential_jitter(initial=1, max=60),
        stop=stop_after_attempt(5),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying {method} {url} (attempt {retry_state.attempt_number}) after error: {retry_state.outcome.exception()}"
        )
    )
    def _do_request():
        response = session.request(method, url, **kwargs)
        if response.status_code != 200:
            # Raise custom error to trigger retry if it's retryable
            raise HTTPError(response.status_code, response.reason)
        return response
        
    return _do_request()
