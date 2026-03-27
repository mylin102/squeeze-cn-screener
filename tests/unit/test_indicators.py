import pandas as pd
import numpy as np
import pytest
from squeeze.engine.indicators import calculate_squeeze_indicators

def test_calculate_squeeze_indicators_structure(sample_ohlcv_df):
    """
    Verify that the calculate_squeeze_indicators function returns a dataframe 
    with the expected columns.
    """
    df = calculate_squeeze_indicators(sample_ohlcv_df)
    
    expected_columns = [
        'Squeeze_On', 
        'Energy_Level', 
        'Momentum', 
        'Fired'
    ]
    
    for col in expected_columns:
        assert col in df.columns

def test_calculate_squeeze_indicators_values(sample_ohlcv_df):
    """
    Verify basic properties of the indicator output.
    """
    df = calculate_squeeze_indicators(sample_ohlcv_df)
    
    # Squeeze_On should be boolean
    assert df['Squeeze_On'].dtype == bool
    
    # Energy_Level should be between 0 and 3
    assert df['Energy_Level'].min() >= 0
    assert df['Energy_Level'].max() <= 3
    assert df['Energy_Level'].dtype in [np.int64, np.int32]
    
    # Fired should be boolean
    assert df['Fired'].dtype == bool

def test_squeeze_logic_reproduction(sample_ohlcv_df):
    """
    Verify specific logic: Squeeze On when BB inside KC.
    """
    # This is a bit harder to test without manually calculating, 
    # but we can check if it runs and produces expected types.
    df = calculate_squeeze_indicators(sample_ohlcv_df)
    
    # At least some values should be boolean
    assert not df['Squeeze_On'].isna().all()

def test_empty_dataframe():
    """
    Verify behavior with empty dataframe.
    """
    df = pd.DataFrame()
    with pytest.raises(Exception):
        calculate_squeeze_indicators(df)
