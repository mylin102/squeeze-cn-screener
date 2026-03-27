import logging
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

EASTMONEY_KLINE_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
PERIOD_LIMIT_MAP = {
    "1mo": 22,
    "3mo": 66,
    "6mo": 132,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
    "max": 5000,
}


def download_market_data(tickers: list[str], period: str = "1y") -> pd.DataFrame:
    """
    Download daily OHLC data for a list of tickers.

    Primary source: Eastmoney daily kline API for China A-shares.
    Fallback source: yfinance.
    """
    if not tickers:
        logger.warning("No tickers provided for download.")
        return pd.DataFrame()

    all_frames: list[pd.DataFrame] = []
    failed_tickers: list[str] = []

    for ticker in tickers:
        df = _download_single_ticker_from_eastmoney(ticker, period=period)
        if df is not None and not df.empty:
            all_frames.append(pd.concat({ticker: df}, axis=1))
        else:
            failed_tickers.append(ticker)

    if failed_tickers:
        logger.warning(
            "Eastmoney data unavailable for %d tickers. Falling back to yfinance.",
            len(failed_tickers),
        )
        fallback_df = _download_with_yfinance(failed_tickers, period=period)
        if not fallback_df.empty:
            all_frames.append(fallback_df)

    if not all_frames:
        logger.warning("No data found for any tickers.")
        return pd.DataFrame()

    return pd.concat(all_frames, axis=1).sort_index(axis=1)


def _download_single_ticker_from_eastmoney(ticker: str, period: str) -> Optional[pd.DataFrame]:
    secid = _eastmoney_secid(ticker)
    if secid is None:
        logger.debug("Ticker %s is not supported by Eastmoney secid mapping.", ticker)
        return None

    params = {
        "secid": secid,
        "klt": "101",
        "fqt": "1",
        "lmt": str(PERIOD_LIMIT_MAP.get(period, 252)),
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/",
    }

    try:
        response = requests.get(EASTMONEY_KLINE_URL, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        klines = payload.get("data", {}).get("klines", []) or []
        if not klines:
            return None
        return _parse_eastmoney_klines(klines)
    except Exception as exc:
        logger.debug("Eastmoney download failed for %s: %s", ticker, exc)
        return None


def _download_with_yfinance(tickers: list[str], period: str) -> pd.DataFrame:
    chunk_size = 100
    all_chunks = []

    for i in range(0, len(tickers), chunk_size):
        chunk = tickers[i:i + chunk_size]
        logger.info("Downloading yfinance fallback chunk %d (%d tickers)...", i // chunk_size + 1, len(chunk))
        try:
            df = yf.download(
                tickers=chunk,
                period=period,
                interval="1d",
                group_by="ticker",
                threads=True,
                progress=False,
            )
            if not df.empty:
                all_chunks.append(df)
        except Exception as exc:
            logger.error("Error downloading yfinance fallback chunk starting at %d: %s", i, exc)

    if not all_chunks:
        return pd.DataFrame()
    return pd.concat(all_chunks, axis=1)


def _eastmoney_secid(ticker: str) -> Optional[str]:
    if "." not in ticker:
        return None
    code, suffix = ticker.split(".", 1)
    if suffix == "SS":
        return f"1.{code}"
    if suffix == "SZ":
        return f"0.{code}"
    return None


def _parse_eastmoney_klines(klines: list[str]) -> pd.DataFrame:
    rows = []
    for item in klines:
        parts = item.split(",")
        if len(parts) < 6:
            continue
        rows.append(
            {
                "Date": parts[0],
                "Open": float(parts[1]),
                "Close": float(parts[2]),
                "High": float(parts[3]),
                "Low": float(parts[4]),
                "Volume": float(parts[5]),
            }
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date")
    return df[["Open", "High", "Low", "Close", "Volume"]]
