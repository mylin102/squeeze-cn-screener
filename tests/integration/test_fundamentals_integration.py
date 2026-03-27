import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from squeeze.engine.scanner import MarketScanner
from squeeze.engine.patterns import detect_squeeze

@pytest.fixture
def mock_fundamentals_df():
    return pd.DataFrame([
        {
            'ticker': 'HIGH_CAP.TW',
            'marketCap': 2000e9, # 2000B
            'averageVolume': 1000000,
            'trailingPE': 15,
            'priceToBook': 2,
            'dividendYield': 0.03,
            'value_score': 0.8
        },
        {
            'ticker': 'LOW_CAP.TW',
            'marketCap': 50e9, # 50B
            'averageVolume': 50000,
            'trailingPE': 25,
            'priceToBook': 4,
            'dividendYield': 0.01,
            'value_score': 0.3
        }
    ])

def test_scanner_fundamental_filtering(mock_fundamentals_df):
    tickers = ["HIGH_CAP.TW", "LOW_CAP.TW"]
    scanner = MarketScanner(tickers)
    
    # Inject fundamentals
    scanner.fundamentals = mock_fundamentals_df
    
    # Mock data for scan
    dummy_ohlc = pd.DataFrame({
        'Open': [100.0]*100, 'High': [101.0]*100, 'Low': [99.0]*100, 'Close': [100.0]*100, 'Volume': [1000]*100
    })
    multi_data = pd.concat({t: dummy_ohlc for t in tickers}, axis=1)
    scanner.data = multi_data
    
    # 1. Filter by Market Cap (min 100B)
    results = scanner.scan(detect_squeeze, min_mkt_cap=100e9)
    assert len(results) == 1
    assert results[0]['ticker'] == "HIGH_CAP.TW"
    
    # 2. Filter by Value Score (min 0.5)
    results = scanner.scan(detect_squeeze, min_score=0.5)
    assert len(results) == 1
    assert results[0]['ticker'] == "HIGH_CAP.TW"
    
    # 3. No filters
    results = scanner.scan(detect_squeeze)
    assert len(results) == 2

def test_cli_help_includes_filters():
    from typer.testing import CliRunner
    from squeeze.cli import app
    runner = CliRunner()
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--min-mkt-cap" in result.stdout
    assert "--min-price" in result.stdout
