# Phase 1: Core Engine & Data - Research

**Researched:** 2024-05-22 (Updated for 2025 context)
**Domain:** Taiwan Stock Market Data & Technical Analysis Engine
**Confidence:** HIGH

## Summary

This research establishes the foundation for a robust, automated Taiwan stock screener. We identified that the most reliable source for active TWSE/TPEx tickers is the official ISIN service, which provides daily updates on listed securities. For data acquisition, `yfinance` remains the standard for historical OHLC data, provided that specific 2025-era rate-limiting and session management strategies are applied.

**Primary recommendation:** Use the `src` layout with `pyproject.toml` for project structure, and refactor the technical analysis engine to leverage `pandas-ta` for core calculations while maintaining custom logic for specialized patterns like "Houyi Shooting the Sun."

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `yfinance` | >=0.2.54 | Market Data | Ecosystem standard; supports bulk downloads and basic metadata. |
| `pandas-ta` | >=0.3.14b | Technical Indicators | Comprehensive, vectorized, and battle-tested for performance. |
| `pandas` | >=2.0.0 | Data Manipulation | Industry standard for tabular financial data. |
| `typer` | >=0.9.0 | CLI Framework | Type-hint based, modern, and generates excellent help menus. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `requests` | >=2.31.0 | HTTP Client | Fetching ticker lists from ISIN pages. |
| `requests-cache` | >=1.1.0 | API Caching | Prevents redundant downloads during development/backtesting. |
| `rich` | >=13.0.0 | CLI Formatting | Terminal styling, progress bars, and tables. |
| `mplfinance` | >=0.12.0 | Financial Plotting | Standard for OHLC and indicator visualization. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `yfinance` | `FinMind` | FinMind has an official API but may require tokens; `yfinance` is free. |
| `yfinance` | `twstock` | `twstock` is Taiwan-specific but data fetching is often slower/less robust than Yahoo. |
| Custom `squeeze.py` | `pandas-ta` | `pandas-ta` is faster and more tested, but custom logic is needed for proprietary signals. |

## Architecture Patterns

### Recommended Project Structure
Follows the modern `src` layout for Python CLI tools:

```
squeeze-screener/
├── src/
│   └── squeeze/
│       ├── __init__.py
│       ├── __main__.py         # Entry point (python -m squeeze)
│       ├── cli.py              # CLI commands (Typer)
│       ├── data/               # Data fetching & caching
│       │   ├── tickers.py      # TWSE/TPEx ticker discovery
│       │   └── downloader.py   # Bulk yfinance logic
│       ├── engine/             # Technical Analysis
│       │   ├── indicators.py   # Squeeze & custom TA
│       │   └── patterns.py     # Houyi, Whale, etc.
│       ├── reporting/          # Output generation
│       │   ├── exporters.py    # CSV/JSON export
│       │   └── charts.py       # Matplotlib/mplfinance
│       └── utils.py
├── tests/                      # Pytest suite
├── pyproject.toml              # Dependencies & tool config
├── README.md
└── .gitignore
```

### Pattern 1: Ticker Discovery (Official ISIN)
Fetch active tickers directly from the source to avoid "stale" lists.
**Source:** [Official ISIN Service](https://isin.twse.com.tw/isin/C_public.jsp?strMode=2)

### Pattern 2: Bulk Download Batching
To avoid 429 errors from Yahoo Finance, download in batches of 50-100 tickers with random sleep intervals.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Basic Indicators | ATR, KC, BB logic | `pandas-ta` | Performance (vectorized) and edge-case handling. |
| Financial Charts | Manual Matplotlib bars | `mplfinance` | Handles OHLC alignment, volume, and overlays automatically. |
| CLI Args | Manual `sys.argv` | `Typer` | Type safety, auto-help, and nested commands. |
| Data Caching | Manual JSON files | `requests-cache` | Transparent integration with `yfinance` sessions. |

## Common Pitfalls

### Pitfall 1: Taiwan Market Suffixes
**What goes wrong:** `yfinance` returns empty data for tickers like `2330`.
**How to avoid:** Always append `.TW` for TWSE (Listed) and `.TWO` for TPEx (OTC).

### Pitfall 2: Yahoo Finance 429 Errors
**What goes wrong:** IP blocked after fetching ~200 tickers sequentially.
**How to avoid:** 
1. Use `yf.download(list, threads=True)`.
2. Use a `requests` session with a real browser User-Agent.
3. Implement `requests-cache`.

### Pitfall 3: Taiwan Market Holidays
**What goes wrong:** Screener fails on non-trading days or during lunar new year.
**How to avoid:** Check if the returned dataframe is empty before calculation.

## Code Examples

### Bulk Downloading with Session & Cache
```python
import yfinance as yf
import requests_cache
from requests import Session

# Source: yfinance 2025 best practices
session = requests_cache.CachedSession('yfinance.cache', expire_after=3600)
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

def download_data(tickers):
    data = yf.download(
        tickers, 
        period="1y", 
        interval="1d", 
        group_by='ticker', 
        session=session,
        threads=True
    )
    return data
```

### Fetching TWSE Tickers
```python
import pandas as pd
import requests

def fetch_twse_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    res = requests.get(url)
    res.encoding = 'big5'
    df = pd.read_html(res.text)[0]
    # Clean and filter for 4-digit common stocks...
    return df
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `twstock` | `yfinance` + Suffixes | 2023+ | Faster, better international support. |
| Custom TA Loops | `pandas-ta` (Vectorized) | 2022+ | 10x+ speed improvement. |
| `setup.py` | `pyproject.toml` | PEP 621 | Standardized, modern Python packaging. |

## Open Questions

1. **TPEx suffix reliability:** Some sources mention `.TT` for certain TPEx stocks, though `.TWO` is most common. 
   - *Recommendation:* Stick to `.TWO` as primary, fallback to `.TT` if empty.
2. **"Houyi Shooting the Sun" detection:** The exact candle ratio (wick vs. body) is subjective.
   - *Recommendation:* Implement as a configurable strategy with defaults (e.g., wick > 2x body).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/unit` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| 1.1 | Project structure following src layout | Integration | `python -m squeeze --help` | ❌ Wave 0 |
| 1.2 | Ticker fetching returns valid TWSE/TPEx list | Integration | `pytest tests/integration/test_tickers.py` | ❌ Wave 0 |
| 1.3 | Bulk downloader handles 50+ tickers | Integration | `pytest tests/integration/test_download.py` | ❌ Wave 0 |
| 1.4 | Squeeze indicator refactored to pandas-ta | Unit | `pytest tests/unit/test_indicators.py` | ❌ Wave 0 |
| 1.5 | Squeeze logic verified with unit tests | Unit | `pytest tests/unit/test_indicators.py` | ❌ Wave 0 |


### Sampling Rate
- **Per task commit:** `pytest tests/unit`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` — Shared data fixtures (mocked OHLC data).
- [ ] `tests/unit/test_indicators.py` — Baseline accuracy for Squeeze.
- [ ] `tests/integration/test_tickers.py` — Connectivity to ISIN service.

## Sources

### Primary (HIGH confidence)
- [Official TWSE ISIN Service](https://isin.twse.com.tw/isin/C_public.jsp?strMode=2)
- [yfinance Documentation](https://github.com/ranaroussi/yfinance)
- [pandas-ta Documentation](https://github.com/twopirllc/pandas-ta)

### Secondary (MEDIUM confidence)
- [Houyi Pattern community discussions](https://www.google.com/search?q=后羿射日+K線)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Industry standards (pandas-ta, yfinance)
- Architecture: HIGH - src layout is PEP standard
- Pitfalls: HIGH - Common documented issues in TW market scrapers

**Research date:** 2024-05-22
**Valid until:** 2024-12-31
