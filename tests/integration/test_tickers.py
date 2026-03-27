import pytest
from squeeze.data.tickers import fetch_tickers

def test_fetch_tickers_integration():
    """
    Integration test for fetching tickers from official sources.
    Ensures that we get a list of common stocks including some well-known ones.
    """
    tickers = fetch_tickers()
    
    # Should be a list
    assert isinstance(tickers, list)
    
    # Should have more than 1000 items
    assert len(tickers) > 1000
    
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
