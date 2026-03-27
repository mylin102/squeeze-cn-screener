import logging
import pandas as pd
import yfinance as yf
from squeeze.core.session import get_robust_session

# Configure logging
logger = logging.getLogger(__name__)

def download_market_data(tickers: list[str], period: str = '1y') -> pd.DataFrame:
    """
    Download daily OHLC data for a list of tickers using yfinance.
    Uses chunking to avoid rate limits.
    
    Args:
        tickers: List of China stock tickers (e.g., ["600519.SS", "000001.SZ"]).
        period: Data period to download (default: '1y').
        
    Returns:
        pd.DataFrame: MultiIndex dataframe grouped by ticker.
    """
    if not tickers:
        logger.warning("No tickers provided for download.")
        return pd.DataFrame()
        
    # Implement chunking to avoid rate limits
    chunk_size = 100
    all_chunks = []
    
    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        logger.info(f"Downloading chunk {i//chunk_size + 1} ({len(chunk)} tickers)...")
        
        try:
            # bulk download
            df = yf.download(
                tickers=chunk,
                period=period,
                interval="1d",
                group_by='ticker',
                threads=True,
                progress=False
            )
            
            if not df.empty:
                all_chunks.append(df)
            
            # Small delay between chunks to be respectful
            if i + chunk_size < len(tickers):
                import time
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error downloading chunk starting at {i}: {str(e)}")
            
    if not all_chunks:
        logger.warning("No data found for any tickers.")
        return pd.DataFrame()
        
    return pd.concat(all_chunks, axis=1)
