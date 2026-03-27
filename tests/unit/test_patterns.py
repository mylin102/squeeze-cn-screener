import pandas as pd
import numpy as np
import pytest
from squeeze.engine.patterns import detect_houyi_shooting_sun, detect_whale_trading

def create_base_df(days=100, price=100.0, volatility=2.0):
    """
    Create a base DataFrame with stable prices (likely to be in a Squeeze).
    Higher volatility (High-Low) makes KC wider, increasing Squeeze chance.
    """
    dates = pd.date_range(end='2026-03-18', periods=days)
    df = pd.DataFrame({
        'Open': np.full(days, price),
        'High': np.full(days, price + volatility),
        'Low': np.full(days, price - volatility),
        'Close': np.full(days, price),
        'Volume': 1000
    }, index=dates)
    return df

def test_houyi_perfect_setup():
    """Test Case 1: Perfect Houyi setup (Rally -> Fib Retrace -> Squeeze -> Shooting Star) -> Match."""
    days = 100
    df = create_base_df(days=days)
    
    # 1. Create a massive rally (Day 30 to 50)
    # Peak at 200. Trough at 100.
    rally_prices = np.linspace(100, 200, 21)
    df.iloc[30:51, df.columns.get_loc('Close')] = rally_prices
    df.iloc[30:51, df.columns.get_loc('High')] = rally_prices + 0.1
    df.iloc[30:51, df.columns.get_loc('Low')] = rally_prices - 0.1
    
    # 2. Retrace to 150 (0.5 Fibonacci)
    # Stay at 150 from Day 51 onwards
    df.iloc[51:, df.columns.get_loc('Open')] = 150.0
    df.iloc[51:, df.columns.get_loc('Close')] = 150.0
    df.iloc[51:, df.columns.get_loc('High')] = 150.1
    df.iloc[51:, df.columns.get_loc('Low')] = 149.9
    
    # 3. Add Shooting Star at the very end
    # High spike but close near Open
    last_idx = df.index[-1]
    df.loc[last_idx, 'Open'] = 150.0
    df.loc[last_idx, 'High'] = 160.0
    df.loc[last_idx, 'Low'] = 149.9
    df.loc[last_idx, 'Close'] = 150.1
    
    result = detect_houyi_shooting_sun(df)
    assert result['is_houyi'] == True
    assert result['squeeze_on'] == True
    assert result['shooting_star'] == True

def test_houyi_no_rally():
    """Test Case 2: No Rally -> No Match."""
    df = create_base_df(days=100) # Constant price, no rally
    # Add shooting star
    last_idx = df.index[-1]
    df.loc[last_idx, 'High'] = 110.0
    
    result = detect_houyi_shooting_sun(df)
    assert result['is_houyi'] == False

def test_houyi_no_squeeze():
    """Test Case 3: No Squeeze -> No Match."""
    days = 120
    df = create_base_df(days=days)
    
    # Rally 100 -> 200
    rally_prices = np.linspace(100, 200, 21)
    df.iloc[0:21, df.columns.get_loc('Close')] = rally_prices
    
    # Retrace to 150
    df.iloc[21:, df.columns.get_loc('Close')] = 150.0
    
    # High volatility at the end to break squeeze
    # We make High/Low wide so KC is wide, but we need BB to be even wider.
    # BB width depends on standard deviation of Close.
    # Let's make Close volatile.
    volatile_close = 150 + np.sin(np.linspace(0, 10, 30)) * 50
    df.iloc[-30:, df.columns.get_loc('Close')] = volatile_close
    df.iloc[-30:, df.columns.get_loc('High')] = volatile_close + 10
    df.iloc[-30:, df.columns.get_loc('Low')] = volatile_close - 10
    
    result = detect_houyi_shooting_sun(df)
    assert result['squeeze_on'] == False
    assert result['is_houyi'] == False

def test_whale_perfect_setup():
    """Test Case 1: Squeeze ON (Daily) + Squeeze ON (Weekly) -> Match."""
    # 400 days ~= 80 weeks
    days = 400
    df = create_base_df(days=days, price=100.0) # Use default high volatility
    
    # Ensure upward momentum
    trend = np.linspace(0, 10, days)
    df['Close'] += trend
    df['High'] += trend
    df['Low'] += trend
    df['Open'] += trend
    
    result = detect_whale_trading(df)
    
    assert result['daily_squeeze'] == True
    assert result['weekly_squeeze'] == True
    assert result['daily_momentum'] > 0
    assert result['weekly_momentum'] > 0
    assert result['is_whale'] == True

def test_whale_only_daily_squeeze():
    """Test Case 2: Only Daily Squeeze (High Weekly Volatility) -> No Match."""
    days = 400
    df = create_base_df(days=days)
    
    # Volatile for most of the time (Weekly BB > KC)
    # We need Close to be volatile across weeks.
    volatile_close = 100 + np.sin(np.linspace(0, 40, days)) * 50
    df['Close'] = volatile_close
    df['High'] = volatile_close + 5
    df['Low'] = volatile_close - 5
    
    # Stable for the last 40 days (Daily BB < KC)
    df.iloc[-40:, df.columns.get_loc('Close')] = 100.0
    df.iloc[-40:, df.columns.get_loc('High')] = 100.1
    df.iloc[-40:, df.columns.get_loc('Low')] = 99.9
    
    result = detect_whale_trading(df)
    assert result['daily_squeeze'] == True
    assert result['weekly_squeeze'] == False
    assert result['is_whale'] == False

def test_whale_both_squeezed_negative_momentum():
    """Test Case 3: Both Squeezed but Momentum Negative -> No Match."""
    days = 400
    df = create_base_df(days=days)
    
    # Downward trend
    trend = np.linspace(0, -20, days)
    df['Close'] += trend
    df['High'] += trend
    df['Low'] += trend
    df['Open'] += trend
    
    result = detect_whale_trading(df)
    assert result['is_whale'] == False
    assert result['daily_momentum'] < 0
