import json
from importlib import resources
import requests
from typing import List, Dict

def fetch_tickers() -> List[str]:
    """
    Backward compatibility for existing code.
    """
    mapping = fetch_tickers_with_names()
    return sorted(list(mapping.keys()))

def fetch_tickers_with_names() -> Dict[str, str]:
    """
    Fetch China A-share tickers and names.
    Primary source: Eastmoney public quote list.
    Secondary source: bundled snapshot shipped with the project.
    """
    ticker_map = _fetch_from_eastmoney()
    if ticker_map:
        return ticker_map

    print("Falling back to bundled China A-share snapshot.")
    return _load_seed_ticker_map()


def _fetch_from_eastmoney() -> Dict[str, str]:
    ticker_map = {}
    base_url = "https://push2.eastmoney.com/api/qt/clist/get"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://quote.eastmoney.com/",
    }
    params = {
        "pn": 1,
        "pz": 5000,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f3",
        # Shenzhen main board + ChiNext, Shanghai main board + STAR board.
        "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        "fields": "f12,f14",
    }

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        diff = payload.get("data", {}).get("diff", []) or []

        for row in diff:
            code = str(row.get("f12", "")).strip()
            name = str(row.get("f14", "")).strip()
            if not code or not code.isdigit() or not name:
                continue

            if code.startswith(("6", "688")):
                suffix = ".SS"
            elif code.startswith(("0", "3")):
                suffix = ".SZ"
            else:
                continue

            ticker_map[f"{code}{suffix}"] = name
    except Exception as e:
        print(f"Error fetching China A-share stocks: {e}")
    return ticker_map


def _load_seed_ticker_map() -> Dict[str, str]:
    with resources.files("squeeze.data").joinpath("cn_seed_tickers.json").open("r", encoding="utf-8") as fh:
        return json.load(fh)
