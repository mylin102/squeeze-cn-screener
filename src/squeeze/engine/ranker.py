import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def calculate_value_score(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates a Value Score (0-1) for each stock in the DataFrame based on 
    percentile ranking of P/E, P/B, and Dividend Yield.
    
    Formula: (Rank(1/PE) + Rank(1/PB) + Rank(Yield)) / 3
    
    Args:
        df: DataFrame containing fundamental metrics.
        
    Returns:
        pd.DataFrame: Original DataFrame with a 'value_score' column.
    """
    if df.empty:
        return df
        
    res = df.copy()
    
    # We want LOWER P/E and P/B to have HIGHER ranks.
    # We use rank(pct=True, ascending=False) for this.
    # Dividend Yield: HIGHER is BETTER, so ascending=True.
    
    # PE Rank (Lower is better)
    if 'trailingPE' in res.columns:
        # Handle cases where PE might be negative or extremely high
        # pct rank handles this naturally. NaNs will be NaN in result.
        res['pe_rank'] = res['trailingPE'].rank(pct=True, ascending=False)
    else:
        res['pe_rank'] = 0.5 # Default middle rank
        
    # PB Rank (Lower is better)
    if 'priceToBook' in res.columns:
        res['pb_rank'] = res['priceToBook'].rank(pct=True, ascending=False)
    else:
        res['pb_rank'] = 0.5
        
    # Yield Rank (Higher is better)
    if 'dividendYield' in res.columns:
        res['yield_rank'] = res['dividendYield'].rank(pct=True, ascending=True)
    else:
        res['yield_rank'] = 0.5
        
    # Combine ranks into final Value Score
    # fillna(0.5) to give neutral score to missing metrics
    score_cols = ['pe_rank', 'pb_rank', 'yield_rank']
    res['value_score'] = res[score_cols].fillna(0.5).mean(axis=1)
    
    # Clean up intermediate rank columns
    res = res.drop(columns=score_cols)
    
    return res
