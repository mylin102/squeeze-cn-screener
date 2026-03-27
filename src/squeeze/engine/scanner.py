import logging
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, List, Dict, Any, Optional
import numpy as np
from squeeze.data.downloader import download_market_data
from squeeze.data.fundamentals import get_fundamentals
from squeeze.engine.ranker import calculate_value_score

# Configure logging
logger = logging.getLogger(__name__)

class MarketScanner:
    """
    MarketScanner handles high-performance market-wide scanning for patterns.
    Uses a hybrid approach:
    - Threading for I/O bound data fetching (via yfinance).
    - Multiprocessing for CPU bound pattern detection.
    """
    
    def __init__(self, tickers: List[str], ticker_names: Optional[Dict[str, str]] = None):
        """
        Initialize the scanner with a list of tickers.
        
        Args:
            tickers: List of ticker strings (e.g., ["600519.SS", "000001.SZ"]).
            ticker_names: Optional dictionary mapping ticker to Chinese name.
        """
        self.tickers = tickers
        self.ticker_names = ticker_names or {}
        self.data: pd.DataFrame = pd.DataFrame()
        self.fundamentals: pd.DataFrame = pd.DataFrame()
        self.results: List[Dict[str, Any]] = []

    def fetch_data(self, period: str = "2y", data: pd.DataFrame = None):
        """
        Fetch market data for all tickers or use provided data.
        """
        if data is not None:
            self.data = data
            return self.data
            
        logger.info(f"Fetching data for {len(self.tickers)} tickers...")
        self.data = download_market_data(self.tickers, period=period)
        return self.data

    def fetch_fundamentals(self):
        """
        Fetch fundamental data for all tickers and calculate Value Score.
        """
        logger.info(f"Fetching fundamentals for {len(self.tickers)} tickers...")
        raw_fundamentals = get_fundamentals(self.tickers)
        if not raw_fundamentals.empty:
            self.fundamentals = calculate_value_score(raw_fundamentals)
        return self.fundamentals

    def scan(self, 
             pattern_fn: Callable[[pd.DataFrame], Dict[str, Any]], 
             min_mkt_cap: Optional[float] = None,
             min_avg_volume: Optional[float] = None,
             min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Scan the downloaded market data for a given pattern and apply fundamental filters.
        """
        if self.data.empty:
            logger.warning("No data to scan. Call fetch_data() first.")
            return []

        # 1. Apply fundamental filters first if data is available
        filtered_tickers = self.tickers
        fundamental_map = {}
        
        if not self.fundamentals.empty:
            df_fund = self.fundamentals.copy()
            
            # Apply filters
            if min_mkt_cap is not None:
                df_fund = df_fund[df_fund['marketCap'] >= min_mkt_cap]
            if min_avg_volume is not None:
                df_fund = df_fund[df_fund['averageVolume'] >= min_avg_volume]
            if min_score is not None:
                df_fund = df_fund[df_fund['value_score'] >= min_score]
                
            filtered_tickers = df_fund['ticker'].tolist()
            # Create a map for easy lookup later
            fundamental_map = df_fund.set_index('ticker').to_dict('index')
            logger.info(f"Fundamental filtering reduced tickers from {len(self.tickers)} to {len(filtered_tickers)}")

        # 2. Prepare ticker tasks
        tasks = []
        if len(self.tickers) == 1:
            ticker = self.tickers[0]
            if ticker in filtered_tickers and not self.data.empty:
                tasks.append((ticker, self.data))
        else:
            for ticker in filtered_tickers:
                try:
                    if ticker in self.data.columns.levels[0]:
                        ticker_df = self.data[ticker].dropna(subset=['Close'])
                        if not ticker_df.empty:
                            tasks.append((ticker, ticker_df))
                except (KeyError, AttributeError):
                    continue

        if not tasks:
            logger.warning("No valid ticker data found to scan after filtering.")
            return []

        # 3. Pattern Detection (Multiprocessing)
        results = []
        with ProcessPoolExecutor() as executor:
            future_to_ticker = {executor.submit(pattern_fn, df): ticker for ticker, df in tasks}
            
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    result['ticker'] = ticker
                    result['name'] = self.ticker_names.get(ticker, "未知")
                    
                    # Merge fundamental data into results
                    if ticker in fundamental_map:
                        result.update(fundamental_map[ticker])
                        
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error scanning ticker {ticker}: {str(e)}")
                    results.append({
                        'ticker': ticker,
                        'name': self.ticker_names.get(ticker, "未知"),
                        'error': str(e),
                        'is_squeezed': False
                    })
        
        self.results = results
        return results
