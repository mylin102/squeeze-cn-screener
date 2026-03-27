from unittest.mock import Mock, patch

import pandas as pd

from squeeze.data.downloader import download_market_data, load_market_data_cache, save_market_data_cache


def test_download_market_data_prefers_eastmoney():
    payload = {
        "data": {
            "klines": [
                "2026-03-20,10,10.5,10.8,9.9,100000,0,0,0,0,0",
                "2026-03-21,10.5,10.7,10.9,10.2,120000,0,0,0,0,0",
            ]
        }
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    with patch("squeeze.data.downloader.requests.get", return_value=response), patch(
        "squeeze.data.downloader.yf.download"
    ) as mock_yf:
        df = download_market_data(["600519.SS"], period="1mo")

    assert not df.empty
    assert "600519.SS" in df.columns.get_level_values(0)
    assert ("600519.SS", "Close") in df.columns
    assert float(df[("600519.SS", "Close")].iloc[-1]) == 10.7
    mock_yf.assert_not_called()


def test_download_market_data_falls_back_to_yfinance():
    yf_df = pd.concat(
        {
            "000001.SZ": pd.DataFrame(
                {
                    "Open": [10.0],
                    "High": [10.5],
                    "Low": [9.8],
                    "Close": [10.2],
                    "Volume": [100000],
                },
                index=pd.to_datetime(["2026-03-21"]),
            )
        },
        axis=1,
    )

    with patch("squeeze.data.downloader.requests.get", side_effect=RuntimeError("dns failure")), patch(
        "squeeze.data.downloader.yf.download", return_value=yf_df
    ):
        df = download_market_data(["000001.SZ"], period="1mo")

    assert not df.empty
    assert ("000001.SZ", "Close") in df.columns


def test_download_market_data_uses_cache_when_complete(tmp_path):
    cache_path = tmp_path / "market_data.pkl"
    cached_df = pd.concat(
        {
            "600519.SS": pd.DataFrame(
                {
                    "Open": [10.0],
                    "High": [10.5],
                    "Low": [9.8],
                    "Close": [10.2],
                    "Volume": [100000],
                },
                index=pd.to_datetime(["2026-03-21"]),
            )
        },
        axis=1,
    )
    save_market_data_cache(cached_df, cache_path)

    with patch("squeeze.data.downloader.requests.get") as mock_requests, patch(
        "squeeze.data.downloader.yf.download"
    ) as mock_yf:
        df = download_market_data(["600519.SS"], period="1mo", cache_path=cache_path)

    assert not df.empty
    assert ("600519.SS", "Close") in df.columns
    mock_requests.assert_not_called()
    mock_yf.assert_not_called()


def test_load_market_data_cache_requires_full_ticker_coverage(tmp_path):
    cache_path = tmp_path / "market_data.pkl"
    cached_df = pd.concat(
        {
            "600519.SS": pd.DataFrame(
                {
                    "Open": [10.0],
                    "High": [10.5],
                    "Low": [9.8],
                    "Close": [10.2],
                    "Volume": [100000],
                },
                index=pd.to_datetime(["2026-03-21"]),
            )
        },
        axis=1,
    )
    save_market_data_cache(cached_df, cache_path)

    loaded_df = load_market_data_cache(cache_path, ["600519.SS", "000001.SZ"])

    assert loaded_df.empty
