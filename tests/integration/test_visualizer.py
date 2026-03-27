import os
import pytest
import pandas as pd
from squeeze.report.visualizer import plot_ticker
from squeeze.engine.indicators import calculate_squeeze_indicators

def test_plot_ticker_generates_file(sample_ohlcv_df, tmp_path):
    """
    Integration test: Call plot_ticker and verify file exists and is not empty.
    """
    ticker = "TSLA"
    # Ensure indicators are present
    df = calculate_squeeze_indicators(sample_ohlcv_df)
    
    # Path in tmp_path
    output_path = str(tmp_path / "tsla_chart.png")
    
    # Run plotting
    plot_ticker(df, ticker, output_path)
    
    # Verify file exists
    assert os.path.exists(output_path)
    
    # Verify file is not zero bytes
    assert os.path.getsize(output_path) > 0

def test_plot_ticker_missing_indicators(sample_ohlcv_df, tmp_path):
    """
    Integration test: Call plot_ticker with raw OHLCV and it should still work.
    """
    ticker = "AAPL"
    output_path = str(tmp_path / "aapl_chart.png")
    
    # Plot with raw OHLCV
    plot_ticker(sample_ohlcv_df, ticker, output_path)
    
    # Verify file exists and is not zero
    assert os.path.exists(output_path)
    assert os.path.getsize(output_path) > 0
