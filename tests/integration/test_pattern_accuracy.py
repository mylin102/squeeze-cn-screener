import pytest
import pandas as pd
from squeeze.engine.scanner import MarketScanner
from squeeze.engine.patterns import detect_squeeze, detect_houyi_shooting_sun, detect_whale_trading

def test_full_pattern_suite_integration(mock_tickers):
    """
    Test all patterns against a few real tickers to ensure no crashes and consistent metadata.
    """
    # Use 2 years of data for Whale pattern (needs enough bars for weekly resampling)
    scanner = MarketScanner(mock_tickers[:5]) 
    scanner.fetch_data(period="2y")
    
    patterns = [
        ("squeeze", detect_squeeze),
        ("houyi", detect_houyi_shooting_sun),
        ("whale", detect_whale_trading)
    ]
    
    for name, fn in patterns:
        results = scanner.scan(fn)
        assert len(results) > 0
        for res in results:
            assert 'ticker' in res
            # Check for pattern-specific keys
            if name == "squeeze":
                assert 'is_squeezed' in res
            elif name == "houyi":
                assert 'is_houyi' in res
                assert 'rally_pct' in res
            elif name == "whale":
                assert 'is_whale' in res
                assert 'daily_squeeze' in res
                assert 'weekly_squeeze' in res

def test_whale_alignment_logic_with_injected_data(sample_ohlcv_df):
    """
    Verify Whale Trading logic correctly handles daily-to-weekly alignment.
    """
    # Create enough data for weekly (at least 100 days)
    full_data = pd.concat([sample_ohlcv_df] * 5)
    full_data.index = pd.date_range(end='2026-03-18', periods=len(full_data))
    
    result = detect_whale_trading(full_data)
    assert 'is_whale' in result
    assert isinstance(result['daily_squeeze'], bool)
    assert isinstance(result['weekly_squeeze'], bool)
