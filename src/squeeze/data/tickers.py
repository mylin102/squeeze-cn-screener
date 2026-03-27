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
    Fetch China A-share tickers and names from Eastmoney public quote lists.
    Returns a dictionary mapping ticker symbols (.SS/.SZ) to Chinese names.
    """
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
