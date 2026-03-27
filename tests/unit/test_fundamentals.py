import pytest
import pandas as pd
from squeeze.data.fundamentals import get_fundamentals
from unittest.mock import MagicMock, patch

@patch("yfinance.Tickers")
def test_get_fundamentals_success(mock_tickers):
    # Setup mock
    mock_ticker_obj = MagicMock()
    mock_ticker_obj.info = {
        'marketCap': 1000000,
        'trailingPE': 15.5,
        'priceToBook': 2.1,
        'dividendYield': 0.03,
        'averageVolume': 50000,
        'sector': 'Technology'
    }
    
    # yf.Tickers returns an object with a .tickers dict
    instance = mock_tickers.return_value
    instance.tickers = {"600519.SS": mock_ticker_obj}
    
    df = get_fundamentals(["600519.SS"])
    
    assert len(df) == 1
    assert df.iloc[0]['ticker'] == "600519.SS"
    assert df.iloc[0]['marketCap'] == 1000000
    assert df.iloc[0]['sector'] == "Technology"

@patch("yfinance.Tickers")
def test_get_fundamentals_empty(mock_tickers):
    df = get_fundamentals([])
    assert df.empty

@patch("yfinance.Tickers")
def test_get_fundamentals_error_handling(mock_tickers):
    # Setup mock to raise error for one ticker
    instance = mock_tickers.return_value
    instance.tickers = {"INVALID": MagicMock()}
    instance.tickers["INVALID"].info = {} # Simulating missing info or error
    
    # Let's mock the loop to fail
    with patch("squeeze.data.fundamentals.logger") as mock_logger:
        df = get_fundamentals(["INVALID"])
        assert "ticker" in df.columns
        # Depending on how the loop is implemented, it might have NaN or empty values
