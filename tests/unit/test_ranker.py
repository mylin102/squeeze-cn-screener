import pytest
import pandas as pd
import numpy as np
from squeeze.engine.ranker import calculate_value_score

def test_calculate_value_score_logic():
    data = {
        'ticker': ['A', 'B', 'C'],
        'trailingPE': [10, 20, 30], # A is best
        'priceToBook': [1, 2, 3],   # A is best
        'dividendYield': [0.05, 0.03, 0.01] # A is best
    }
    df = pd.DataFrame(data)
    
    result = calculate_value_score(df)
    
    assert 'value_score' in result.columns
    # A should have the highest score since it's best in all metrics
    assert result.iloc[0]['value_score'] > result.iloc[1]['value_score']
    assert result.iloc[1]['value_score'] > result.iloc[2]['value_score']

def test_calculate_value_score_with_nans():
    data = {
        'ticker': ['A', 'B', 'C'],
        'trailingPE': [10, np.nan, 30],
        'priceToBook': [1, 2, np.nan],
        'dividendYield': [np.nan, 0.03, 0.01]
    }
    df = pd.DataFrame(data)
    
    result = calculate_value_score(df)
    assert not result['value_score'].isna().any()

def test_calculate_value_score_empty():
    df = pd.DataFrame()
    result = calculate_value_score(df)
    assert result.empty
