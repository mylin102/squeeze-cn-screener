import pytest
import pandas as pd
from squeeze.data.downloader import download_market_data

def test_download_market_data_success():
    """Verify that we can download data for valid tickers."""
    tickers = ["600519.SS", "000001.SZ"]
    df = download_market_data(tickers, period="1mo")
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    # yf.download with group_by='ticker' results in MultiIndex columns
    # (ticker, OHLCV)
    for ticker in tickers:
        assert ticker in df.columns.get_level_values(0).unique()

def test_download_market_data_invalid_ticker():
    """Verify that the downloader handles invalid tickers gracefully."""
    tickers = ["INVALID_TICKER.SS"]
    # This should log a warning but return an empty or nearly empty DataFrame
    # rather than raising an exception.
    df = download_market_data(tickers, period="1mo")
    
    assert isinstance(df, pd.DataFrame)
    # yfinance often returns an empty DF for invalid tickers
    assert df.empty or "INVALID_TICKER.SS" not in df.columns.get_level_values(0).unique()
