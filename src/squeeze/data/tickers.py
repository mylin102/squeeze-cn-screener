import requests
from typing import List, Dict

FALLBACK_TICKER_MAP = {
    "600519.SS": "Kweichow Moutai",
    "601318.SS": "Ping An Insurance",
    "600036.SS": "China Merchants Bank",
    "600276.SS": "Jiangsu Hengrui Medicine",
    "600309.SS": "Wanhua Chemical",
    "600887.SS": "Yili",
    "601899.SS": "Zijin Mining",
    "603288.SS": "Foshan Haitian",
    "688981.SS": "SMIC",
    "688111.SS": "Beijing Kingsoft Office",
    "000001.SZ": "Ping An Bank",
    "000333.SZ": "Midea Group",
    "000651.SZ": "Gree Electric",
    "000858.SZ": "Wuliangye",
    "000568.SZ": "Luzhou Laojiao",
    "000725.SZ": "BOE",
    "002594.SZ": "BYD",
    "002415.SZ": "Hikvision",
    "002475.SZ": "Luxshare Precision",
    "002714.SZ": "Muyuan Foods",
    "300059.SZ": "East Money Information",
    "300124.SZ": "Shenzhen Inovance",
    "300308.SZ": "CNGR Advanced Material",
    "300750.SZ": "CATL",
    "300760.SZ": "Mindray",
}

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

    if not ticker_map:
        print("Falling back to built-in China A-share seed universe.")
        return FALLBACK_TICKER_MAP.copy()

    return ticker_map
