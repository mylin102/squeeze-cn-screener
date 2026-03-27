import pandas as pd
from squeeze.engine.indicators import calculate_squeeze_indicators

def detect_squeeze(df: pd.DataFrame) -> dict:
    """
    Detect the Squeeze status for a given stock based on its historical data.
    
    Args:
        df: DataFrame with OHLCV data.
        
    Returns:
        dict: A dictionary containing the latest squeeze status:
            - 'is_squeezed' (bool): True if currently in a squeeze.
            - 'energy_level' (int): A value from 0-3 indicating squeeze compression.
            - 'momentum' (float): A normalized momentum value.
            - 'fired' (bool): True if the squeeze just fired.
            - 'timestamp' (str): The date of the analysis.
    """
    if df.empty or len(df) < 30: # Need enough data for indicators
        return {
            'is_squeezed': False,
            'energy_level': 0,
            'momentum': 0.0,
            'fired': False,
            'timestamp': None
        }
        
    # Calculate indicators
    df_with_indicators = calculate_squeeze_indicators(df)
    
    # Get the latest bar
    latest_bar = df_with_indicators.iloc[-1]
    
    return {
        'is_squeezed': bool(latest_bar['Squeeze_On']),
        'energy_level': int(latest_bar['Energy_Level']),
        'momentum': float(latest_bar['Momentum']),
        'prev_momentum': float(latest_bar['Prev_Momentum']),
        'squeeze_on': bool(latest_bar['Squeeze_On']),
        'fired': bool(latest_bar['Fired']),
        'Signal': str(latest_bar.get('Signal', '觀望')),
        'Close': float(latest_bar['Close']),
        'timestamp': str(latest_bar.name)
    }

def detect_houyi_shooting_sun(df: pd.DataFrame) -> dict:
    """
    Detect the 'Houyi Shooting the Sun' pattern.
    
    Criteria:
    1. Rally: >20% gain in a 30-day window within the last 60 days.
    2. Retracement: Current price within 0.5 - 0.7 Fibonacci retracement of that rally.
    3. Squeeze: TTM Squeeze is ON.
    4. Shooting Star: Upper wick >= 2x real body in the last 5 bars.
    
    Args:
        df: DataFrame with OHLCV data.
        
    Returns:
        dict: Pattern detection results and metadata.
    """
    if df.empty or len(df) < 60:
        return {
            'is_houyi': False,
            'rally_pct': 0.0,
            'fib_level': 0.0,
            'squeeze_on': False,
            'shooting_star': False
        }

    # 1. Calculate Indicators
    df_indicators = calculate_squeeze_indicators(df)
    latest_bar = df_indicators.iloc[-1]
    
    # 2. Rally & Fib Detection
    # Look back 60 bars to find the highest high
    lookback = 60
    window = df.iloc[-lookback:]
    peak_idx = window['High'].idxmax()
    peak_price = window['High'].max()
    
    # Find the lowest low in the 30 days preceding that peak
    peak_pos = df.index.get_loc(peak_idx)
    start_pos = max(0, peak_pos - 30)
    preceding_window = df.iloc[start_pos:peak_pos + 1]
    trough_price = preceding_window['Low'].min()
    
    rally_pct = (peak_price - trough_price) / trough_price if trough_price > 0 else 0
    
    # Current price vs Fib levels
    current_price = latest_bar['Close']
    if peak_price > trough_price:
        fib_level = (peak_price - current_price) / (peak_price - trough_price)
    else:
        fib_level = 0.0
        
    # 3. Squeeze Check
    squeeze_on = bool(latest_bar['Squeeze_On'])
    
    # 4. Shooting Star Check (most recent 5 bars)
    shooting_star = False
    recent_bars = df.iloc[-5:]
    for _, bar in recent_bars.iterrows():
        body = abs(bar['Close'] - bar['Open'])
        upper_wick = bar['High'] - max(bar['Close'], bar['Open'])
        if body < 0.001: # Avoid division by zero for Doji-like stars
            if upper_wick > 0:
                shooting_star = True
                break
        elif (upper_wick / body) >= 2.0:
            shooting_star = True
            break
            
    is_houyi = bool(
        rally_pct >= 0.2 and
        0.4 <= fib_level <= 0.75 and # Range encompassing 0.5-0.618 with some buffer
        squeeze_on and
        shooting_star
    )
    
    return {
        'is_houyi': is_houyi,
        'rally_pct': float(rally_pct),
        'fib_level': float(fib_level),
        'squeeze_on': squeeze_on,
        'energy_level': int(latest_bar['Energy_Level']),
        'momentum': float(latest_bar['Momentum']),
        'prev_momentum': float(latest_bar['Prev_Momentum']),
        'fired': bool(latest_bar['Fired']),
        'shooting_star': shooting_star,
        'Close': float(latest_bar['Close']),
        'Signal': str(latest_bar.get('Signal', '觀望'))
    }

def detect_whale_trading(df_daily: pd.DataFrame) -> dict:
    """
    Detect the 'Whale Trading' multi-timeframe alignment pattern.
    
    Criteria:
    1. Daily Squeeze ON.
    2. Weekly Squeeze ON.
    3. Momentum not deeply negative on both (>-0.5).
    
    Args:
        df_daily: DataFrame with Daily OHLCV data.
        
    Returns:
        dict: Pattern detection results and metadata.
    """
    if df_daily.empty or len(df_daily) < 100:
        return {
            'is_whale': False,
            'daily_squeeze': False,
            'weekly_squeeze': False,
            'daily_momentum': 0.0,
            'weekly_momentum': 0.0
        }

    # 1. Daily indicators
    df_daily_res = calculate_squeeze_indicators(df_daily)
    latest_daily = df_daily_res.iloc[-1]
    
    # 2. Resample to Weekly
    # Ensure index is datetime for resampling
    if not isinstance(df_daily.index, pd.DatetimeIndex):
        df_daily.index = pd.to_datetime(df_daily.index)
        
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    df_weekly = df_daily.resample('W').apply(logic).dropna()
    
    if len(df_weekly) < 30:
        return {
            'is_whale': False,
            'daily_squeeze': bool(latest_daily['Squeeze_On']),
            'weekly_squeeze': False,
            'daily_momentum': float(latest_daily['Momentum']),
            'weekly_momentum': 0.0
        }
        
    # 3. Weekly indicators
    df_weekly_res = calculate_squeeze_indicators(df_weekly)
    latest_weekly = df_weekly_res.iloc[-1]
    
    # 4. Alignment
    daily_sq = bool(latest_daily['Squeeze_On'])
    weekly_sq = bool(latest_weekly['Squeeze_On'])
    daily_mom = float(latest_daily['Momentum'])
    weekly_mom = float(latest_weekly['Momentum'])
    
    # Signal if both are squeezed and momentum is positive
    is_whale = daily_sq and weekly_sq and daily_mom > 0 and weekly_mom > 0
    
    return {
        'is_whale': bool(is_whale),
        'daily_squeeze': daily_sq,
        'weekly_squeeze': weekly_sq,
        'squeeze_on': daily_sq,
        'daily_momentum': daily_mom,
        'weekly_momentum': weekly_mom,
        'momentum': daily_mom,
        'prev_momentum': float(df_daily_res.iloc[-1]['Prev_Momentum']),
        'energy_level': int(latest_daily['Energy_Level']),
        'fired': bool(latest_daily['Fired']),
        'Close': float(latest_daily['Close']),
        'Signal': str(latest_daily.get('Signal', '觀望'))
    }
