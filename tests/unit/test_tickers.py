from unittest.mock import Mock, patch

from squeeze.data.tickers import fetch_tickers_with_names


def test_fetch_tickers_uses_bundled_snapshot_when_primary_fails():
    with patch("squeeze.data.tickers.requests.get", side_effect=RuntimeError("network down")):
        tickers = fetch_tickers_with_names()

    assert len(tickers) >= 25
    assert tickers["600519.SS"] == "Kweichow Moutai"
    assert tickers["000001.SZ"] == "Ping An Bank"


def test_fetch_tickers_prefers_primary_source():
    payload = {
        "data": {
            "diff": [
                {"f12": "600519", "f14": "Kweichow Moutai"},
                {"f12": "000001", "f14": "Ping An Bank"},
            ]
        }
    }
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload

    with patch("squeeze.data.tickers.requests.get", return_value=response):
        tickers = fetch_tickers_with_names()

    assert tickers == {
        "600519.SS": "Kweichow Moutai",
        "000001.SZ": "Ping An Bank",
    }
