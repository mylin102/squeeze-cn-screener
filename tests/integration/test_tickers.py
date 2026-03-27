import pytest
from squeeze.data.tickers import fetch_tickers

def test_fetch_tickers_integration():
    """
    Integration test for fetching tickers from the configured source stack.
    Ensures that we get a usable list even when the primary source is unavailable.
    """
    tickers = fetch_tickers()
    
    # Should be a list
    assert isinstance(tickers, list)
    
    # Should have a usable universe, even if we fall back to the bundled snapshot
    assert len(tickers) >= 25
    
    # Should contain some known tickers with correct suffixes
    assert "600519.SS" in tickers  # Kweichow Moutai
    assert "601318.SS" in tickers  # Ping An Insurance
    assert "000001.SZ" in tickers  # Ping An Bank
    
    # Tickers should only be digits + suffix
    for t in tickers:
        code, suffix = t.split('.')
        assert code.isdigit()
        assert len(code) == 6
        assert suffix in ["SS", "SZ"]
