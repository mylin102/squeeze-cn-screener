import pandas as pd
import mplfinance as mpf
import pandas_ta as ta
import numpy as np
import os

def plot_ticker(ticker_df: pd.DataFrame, ticker_symbol: str, output_path: str):
    """
    Generates a candlestick chart with technical indicators for a given ticker.
    Optimized: 1-year view, separate Squeeze State Panel for high visibility.
    """
    # 1. Ensure index is DatetimeIndex and sorted
    if not isinstance(ticker_df.index, pd.DatetimeIndex):
        ticker_df.index = pd.to_datetime(ticker_df.index)
    df = ticker_df.sort_index().copy()
    
    # 2. Ensure Squeeze indicators exist
    if 'Momentum' not in df.columns or 'Squeeze_On' not in df.columns:
        from squeeze.engine.indicators import calculate_squeeze_indicators
        df = calculate_squeeze_indicators(df)

    # 3. Bollinger Bands & Keltner Channels
    bb = df.ta.bbands(length=20, std=2.0)
    kc = df.ta.kc(length=20, scalar=1.5)
    
    df['BB_Upper'] = bb.filter(like='BBU').iloc[:, 0]
    df['BB_Lower'] = bb.filter(like='BBL').iloc[:, 0]
    df['KC_Upper'] = kc.filter(like='KCU').iloc[:, 0]
    df['KC_Lower'] = kc.filter(like='KCL').iloc[:, 0]

    # 4. Slice to last 1 year (approx 252 trading days)
    plot_df = df.tail(252).copy()
    
    # 5. Prepare indicator plots
    plots = [
        # Main Panel (Panel 0): Channels
        mpf.make_addplot(plot_df['BB_Upper'], color='blue', linestyle='dashed', alpha=0.2),
        mpf.make_addplot(plot_df['BB_Lower'], color='blue', linestyle='dashed', alpha=0.2),
        mpf.make_addplot(plot_df['KC_Upper'], color='orange', alpha=0.2),
        mpf.make_addplot(plot_df['KC_Lower'], color='orange', alpha=0.2),
    ]
    
    # 6. Panel 1: Momentum Histogram
    mom = plot_df['Momentum']
    hist_colors = []
    for i in range(len(mom)):
        val = mom.iloc[i]
        prev_val = mom.iloc[i-1] if i > 0 else 0
        if val >= 0:
            hist_colors.append('cyan' if val >= prev_val else 'blue')
        else:
            hist_colors.append('red' if val <= prev_val else 'maroon')
                
    plots.append(mpf.make_addplot(plot_df['Momentum'], type='bar', panel=1, color=hist_colors, 
                                  secondary_y=False, ylabel='Momentum'))
    
    # 7. Panel 2: Squeeze Status Ribbon (High Visibility)
    squeeze_on = plot_df['Squeeze_On']
    
    # Create a status series: 1.0 for visualization height
    status_val = np.full(len(plot_df), 1.0)
    # Colors: Black for Squeeze ON, Gray for Squeeze OFF
    status_colors = np.where(squeeze_on, 'black', '#cccccc')
    
    plots.append(mpf.make_addplot(status_val, type='bar', panel=2, color=status_colors, 
                                  width=1.0, secondary_y=False, ylabel='SQZ'))

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # 8. Generate Final Plot
    mpf.plot(plot_df, type='candle', style='charles', addplot=plots, 
             title=f"\n{ticker_symbol} - Squeeze Analysis (1yr)", 
             savefig=output_path, volume=True, 
             panel_ratios=(6, 2, 1), 
             datetime_format='%Y-%m',
             xrotation=0,
             show_nontrading=False,
             tight_layout=True)
