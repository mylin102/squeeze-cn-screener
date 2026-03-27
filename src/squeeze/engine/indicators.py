import pandas as pd
import numpy as np
import pandas_ta as ta

def calculate_squeeze_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate PowerSqueeze indicators and explicit Buy/Sell signals.
    
    Args:
        df: DataFrame with OHLCV data.
        
    Returns:
        pd.DataFrame: Original DataFrame with added squeeze indicators and signals.
    """
    if df.empty:
        raise ValueError("Input DataFrame is empty")

    # 1. Standard TTM Squeeze using pandas-ta
    sqz = df.ta.squeeze(bb_length=20, bb_std=2.0, kc_length=20, kc_scalar=1.5, lazy=True)
    
    sqz_on_col = [c for c in sqz.columns if 'SQZ_ON' in c][0]
    mom_col = [c for c in sqz.columns if c.startswith('SQZ_') and c not in ['SQZ_ON', 'SQZ_OFF', 'SQZ_NO']][0]
    
    # 2. Custom Energy Level Calculation
    bb = df.ta.bbands(length=20, std=2.0)
    kc = df.ta.kc(length=20, scalar=1.5)
    
    bb_upper = bb.filter(like='BBU').iloc[:, 0]
    bb_lower = bb.filter(like='BBL').iloc[:, 0]
    kc_upper = kc.filter(like='KCU').iloc[:, 0]
    kc_lower = kc.filter(like='KCL').iloc[:, 0]
    
    bb_width = bb_upper - bb_lower
    kc_width = kc_upper - kc_lower
    
    squeeze_ratio = (kc_width - bb_width) / kc_width
    squeeze_ratio = squeeze_ratio.clip(lower=0, upper=1)
    
    energy_level = pd.cut(
        squeeze_ratio, 
        bins=[-np.inf, 0.3, 0.5, 0.7, np.inf], 
        labels=[0, 1, 2, 3]
    ).fillna(0).astype(int)
    
    # 3. Assemble Results
    result = df.copy()
    result['Squeeze_On'] = sqz[sqz_on_col].astype(bool)
    result['Energy_Level'] = energy_level
    result['Momentum'] = sqz[mom_col].fillna(0)
    
    # Fired: Not squeezed now but was squeezed in the previous bar
    result['Fired'] = (~result['Squeeze_On']) & (result['Squeeze_On'].shift(1) == True)
    result['Fired'] = result['Fired'].fillna(False)

    # 4. Explicit Signal Logic
    # Signals: Strong Buy, Buy, Sell, Wait
    def determine_signal(row):
        mom = row['Momentum']
        prev_mom = row['Prev_Momentum']
        fired = row['Fired']
        sqz_on = row['Squeeze_On']
        
        if fired and mom > 0:
            return "強烈買入 (爆發)"
        if fired and mom < 0:
            return "強烈賣出 (跌破)"
        
        if mom > 0:
            if mom > prev_mom:
                return "買入 (動能增強)"
            else:
                return "觀望 (動能減弱)"
        else: # mom <= 0
            if mom > prev_mom:
                return "觀察 (跌勢收斂)"
            else:
                return "賣出 (動能轉弱)"

    result['Prev_Momentum'] = result['Momentum'].shift(1).fillna(0)
    result['Signal'] = result.apply(determine_signal, axis=1)
    
    return result
