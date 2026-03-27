import pandas as pd
import yfinance as yf
import logging
from typing import List, Dict, Any
from squeeze.core.session import get_robust_session

logger = logging.getLogger(__name__)

def get_fundamentals(tickers: List[str]) -> pd.DataFrame:
    """
    Fetch fundamental data for a list of tickers using yfinance.
    Uses chunking to avoid rate limits and improve reliability.
    
    Args:
        tickers: List of China stock tickers (e.g., ["600519.SS", "000001.SZ"]).
        
    Returns:
        pd.DataFrame: Fundamental metrics for each ticker.
    """
    if not tickers:
        logger.warning("No tickers provided for fundamental fetching.")
        return pd.DataFrame()

    results = []
    chunk_size = 50
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        logger.info(f"Fetching fundamentals chunk {i//chunk_size + 1} ({len(chunk)} tickers)...")
        
        # yf.Tickers allows for some batching efficiency
        try:
            yf_tickers = yf.Tickers(" ".join(chunk))
            
            for ticker_symbol in chunk:
                try:
                    ticker_obj = yf_tickers.tickers[ticker_symbol]
                    info = ticker_obj.info
                    
                    results.append({
                        'ticker': ticker_symbol,
                        'marketCap': info.get('marketCap'),
                        'trailingPE': info.get('trailingPE'),
                        'priceToBook': info.get('priceToBook'),
                        'dividendYield': info.get('dividendYield'),
                        'averageVolume': info.get('averageVolume'),
                        'sector': info.get('sector')
                    })
                except Exception as e:
                    logger.debug(f"Error fetching fundamentals for {ticker_symbol}: {str(e)}")
                    results.append({
                        'ticker': ticker_symbol,
                        'error': str(e)
                    })
            
            # Small delay between chunks
            if i + chunk_size < len(tickers):
                import time
                time.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error processing fundamentals chunk starting at {i}: {str(e)}")
            
    return pd.DataFrame(results)
