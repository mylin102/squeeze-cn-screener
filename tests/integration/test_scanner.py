import pytest
import pandas as pd
from squeeze.engine.scanner import MarketScanner
from squeeze.engine.patterns import detect_squeeze

def test_market_scanner_initialization():
    tickers = ["600519.SS", "000001.SZ"]
    scanner = MarketScanner(tickers)
    assert scanner.tickers == tickers
    assert scanner.data.empty
    assert scanner.results == []

def test_market_scanner_fetch_and_scan(mock_tickers):
    """
    Test the full fetch and scan cycle with a small set of tickers.
    Note: This makes real network requests unless mocked.
    """
    scanner = MarketScanner(mock_tickers)
    
    # Fetch data (limiting period for speed)
    df = scanner.fetch_data(period="1mo")
    assert not df.empty
    
    # Scan for squeeze
    results = scanner.scan(detect_squeeze)
    
    assert len(results) > 0
    for res in results:
        assert 'ticker' in res
        assert 'is_squeezed' in res
        assert 'energy_level' in res
        assert 'momentum' in res

def test_market_scanner_with_injected_data(sample_ohlcv_df):
    """
    Test scanning with pre-provided data to avoid network calls.
    """
    ticker = "600519.SS"
    # Create a MultiIndex dataframe like yfinance returns
    data = pd.concat({ticker: sample_ohlcv_df}, axis=1)
    
    scanner = MarketScanner([ticker])
    scanner.fetch_data(data=data)
    
    results = scanner.scan(detect_squeeze)
    
    assert len(results) == 1
    assert results[0]['ticker'] == ticker
    assert isinstance(results[0]['is_squeezed'], bool)
