# Phase 2: Screener & Pattern Logic - Research

**Researched:** 2026-03-18
**Domain:** Technical Analysis, Pattern Recognition, Performance Scanners
**Confidence:** HIGH

## Summary

This research establishes the precise technical parameters for advanced patterns (Houyi Shooting the Sun, Whale Trading) and the implementation strategy for a high-performance market scanner covering 1000+ Taiwan tickers.

The **primary recommendation** is to use a hybrid architecture: bulk download with `yfinance` (multi-threaded), followed by vectorized indicator calculations using `pandas-ta` within a `multiprocessing` worker pool to maximize CPU utilization for the 1000+ stock scan.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `yfinance` | >=0.2.66 | Market data fetching | Market standard for Yahoo Finance access, supports bulk download. |
| `pandas-ta` | >=0.4.71b0 | Technical indicator engine | Feature-rich, vectorized calculations for Squeeze/ATR/SMA. |
| `pandas` | >=2.2.0 | Data manipulation | Core data structure for high-performance series analysis. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `requests-cache` | >=1.3.1 | Data caching | To avoid re-fetching data for 1000+ stocks during repeated daily scans. |
| `concurrent.futures` | Standard | Parallel processing | To distribute technical analysis across CPU cores. |

**Installation:**
```bash
pip install yfinance pandas-ta requests-cache pandas
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── squeeze/
│   ├── engine/
│   │   ├── scanner.py       # Full-market scan orchestration
│   │   ├── patterns/
│   │   │   ├── houyi.py     # Houyi Shooting the Sun detection logic
│   │   │   └── whale.py     # Whale Trading (Daily+Weekly) alignment
│   └── data/
│       ├── storage.py       # Persistence (Parquet/SQLite)
```

### Pattern 1: Houyi Shooting the Sun (后羿射日)
Based on Growin/LaoWang strategies, this is a **strong-uptrend continuation** pattern.

**Precise Technical Criteria:**
1.  **Phase A (The Sun):** Strong preceding rally (e.g., > 20% gain in 30 days).
2.  **Phase B (The Bow):** Retracement into a Fibonacci zone (0.5 to 0.618 of the Phase A rally).
3.  **Phase C (The Arrow/Squeeze):**
    - Price forms a horizontal "platform" within the retracement zone.
    - **Squeeze ON:** `TTM Squeeze` (BB inside KC) dot is RED/ORANGE.
    - **Candlestick (The Bow Line):** Presence of a "Shooting Star" style candle where **Upper Wick >= 2x Real Body**.
4.  **Phase D (The Shot):** Breakout above the platform high on high volume.

### Pattern 2: Whale Trading (鯨魚交易)
A multi-timeframe alignment pattern identifying institutional accumulation.

**Criteria:**
- `Daily Squeeze == ON` (Energy compressing on daily chart).
- `Weekly Squeeze == ON` (Energy compressing on weekly chart).
- **Confirmation:** Momentum (Histogram) is turning from negative to positive (or increasing positive) on both timeframes.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Squeeze Indicator | Custom math | `pandas_ta.squeeze` | Handles BB/KC/Momentum and edge cases (lazy/non-lazy) accurately. |
| Parallel Data Fetch | `threading` loops | `yf.download(threads=True)` | `yfinance` has built-in, optimized batch downloading for large ticker lists. |
| Cache Management | Manual JSON/Files | `requests-cache` | Drop-in SQLite backend handles TTL and session persistence automatically. |

## Common Pitfalls

### Pitfall 1: Rate Limiting on 1000+ Tickers
- **What goes wrong:** Yahoo Finance blocks IP after too many concurrent requests.
- **How to avoid:** Use `yf.download()` for bulk fetching instead of 1000 separate `Ticker.history()` calls. If using `yfinance` metadata/info, use a `Semaphore` or `Sleep` between batches.

### Pitfall 2: Memory Bloat with Multi-Timeframe Data
- **What goes wrong:** Storing 1000 stocks * 2 timeframes (Daily, Weekly) in memory as separate DataFrames can lead to OOM on small servers (e.g., GitHub Runners).
- **How to avoid:** Process in chunks (e.g., 200 stocks at a time) or store intermediate data in **Parquet** format which is highly compressed.

## Code Examples

### Efficient Scanner Pattern (Hybrid Approach)
```python
import pandas as pd
import yfinance as yf
from concurrent.futures import ProcessPoolExecutor

def analyze_stock(ticker, df_daily, df_weekly):
    # logic to calculate patterns
    return results

def full_market_scan(tickers):
    # 1. Bulk download (I/O bound)
    data = yf.download(tickers, period="2y", group_by='ticker', threads=True)
    
    # 2. Parallel processing (CPU bound)
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(analyze_stock, tickers, ...))
    return results
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Multi-threading for 1k tickers | Bulk batch download | ~2022 (yfinance updates) | 10x speedup, fewer rate limits |
| Manual Fib calculations | `pandas_ta.fibonacci` | - | Standardized levels |

## Open Questions

1.  **Data Reliability:** How often does `yfinance` return incomplete data for TWSE/TPEx stocks? 
    - *Recommendation:* Implement a validation step to ensure the last data point is from "today" before pattern detection.
2.  **Weekly Data Granularity:** Should we fetch Weekly data separately or resample Daily data?
    - *Recommendation:* Resample Daily data to ensure perfect alignment, as `yfinance` weekly data can sometimes have different start/end days.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest` |
| Config file | `pytest.ini` |
| Quick run command | `pytest tests/unit/test_patterns.py` |
| Full suite command | `pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-PAT-01 | Houyi Shooting Sun Detection | Unit | `pytest tests/unit/test_patterns.py -k houyi` | ❌ Wave 0 |
| REQ-PAT-02 | Whale Trading Alignment | Unit | `pytest tests/unit/test_patterns.py -k whale` | ❌ Wave 0 |
| REQ-SCAN-01 | 1000+ Ticker Throughput | Integration | `pytest tests/integration/test_scanner.py` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/unit/test_patterns.py` — implementation of pattern detection unit tests.
- [ ] Mock data generator for synthetic Squeeze and Retracement patterns.

## Sources

### Primary (HIGH confidence)
- `yfinance` Official GitHub - Bulk download documentation.
- `Growin.ai` Technical Blog - "Houyi Shooting the Sun" pattern parameters (0.5-0.618 Fib, Squeeze).
- LaoWang (王倚隆) Public Content - Candlestick "Bow Line" (弓形線) definition.

### Secondary (MEDIUM confidence)
- community-driven TTM Squeeze implementations in Python.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH
- Architecture: HIGH
- Pitfalls: MEDIUM (Rate limiting behavior varies by region)

**Research date:** 2026-03-18
**Valid until:** 2026-04-18
