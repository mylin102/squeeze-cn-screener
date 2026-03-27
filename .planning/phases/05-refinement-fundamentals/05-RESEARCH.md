# Phase 5: Refinement & Fundamentals - Research

**Researched:** 2026-03-18
**Domain:** Fundamental Data, Value Scoring, Reliability & UX
**Confidence:** HIGH

## Summary

This phase focuses on maturing the Squeeze Stock Screener from a technical prototype into a production-ready v1.0 tool. We've verified that `yfinance` provides a rich set of fundamental data for Taiwan stocks (TWSE and TPEx), enabling the implementation of a "Value Score" to filter for high-quality, undervalued opportunities. To ensure reliability, we've identified best practices for session management and exponential backoff to handle Yahoo Finance's rate limiting. Finally, we've outlined the structure for a user-centric guide and a list of "cleanup" tasks to polish the codebase.

**Primary recommendation:** Use a percentile-based "Value Score" (P/E, P/B, Dividend Yield) combined with a robust retry mechanism using `tenacity` and `requests-cache` for high-volume scanning.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| yfinance | 0.2.40+ | Market Data | De-facto standard for free financial data; good TW support. |
| pandas | 2.2.0+ | Data Wrangling | Industry standard for time-series and tabular data. |
| tenacity | 8.2.0+ | Retries | Powerful declarative retry library for robust error handling. |
| requests-cache | 1.1.0+ | Caching | Essential for preventing redundant API calls and rate limits. |
| pyyaml | 6.0.1+ | Configuration | Human-readable configuration format for non-technical users. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| scipy | 1.12.0+ | Percentile Ranking | Used for calculating relative Value Scores across the market. |
| logging | Standard | System Logs | Replacing print statements with structured logging for v1.0. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| yfinance | yahooquery | Often faster but less standard; sometimes different data keys. |
| yfinance | Alpha Vantage | More reliable (paid) but lacks comprehensive Taiwan fundamental data. |

**Installation:**
```bash
pip install yfinance pandas tenacity requests-cache pyyaml scipy
```

## Architecture Patterns

### Recommended Project Structure
```
src/squeeze/
├── config/
│   ├── settings.yaml    # User-editable configuration
│   └── schema.py        # Config validation logic
├── core/
│   ├── session.py       # Centralized requests session with retries/cache
│   └── logging.py       # Centralized logging setup
├── engine/
│   ├── fundamentals.py  # Value Score and F-Score logic
│   └── ...
└── ...
```

### Pattern 1: Percentile-Based Value Scoring
**What:** Ranking stocks relative to the entire scanned universe.
**When to use:** When identifying "cheap" stocks, as absolute P/E ratios vary wildly by sector.
**Example:**
```python
# Calculate Value Score using percentile ranks
df['pe_rank'] = df['trailingPE'].rank(pct=True, ascending=False) # Lower PE = Higher Rank
df['pb_rank'] = df['priceToBook'].rank(pct=True, ascending=False) # Lower PB = Higher Rank
df['yield_rank'] = df['dividendYield'].rank(pct=True) # Higher Yield = Higher Rank

df['value_score'] = (df['pe_rank'] + df['pb_rank'] + df['yield_rank']) / 3
```

### Anti-Patterns to Avoid
- **Hard-coding API keys:** Don't put tokens in the source code; use `config.yaml` or env vars.
- **Aggressive Looping:** Don't call `yf.Ticker().info` in a tight loop without a shared session and delays.
- **Assuming Data Presence:** Always handle `None` or `NaN` values for fundamental data points.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry Logic | Custom `while` loops | `tenacity` | Handles jitter, backoff, and specific exception filtering natively. |
| API Caching | Manual file saving | `requests-cache` | Transparent caching at the network layer. |
| Config Parsing | Custom `.txt` parser | `pyyaml` | Standard, supports nesting and comments. |
| Fundamental Ranks | Custom sorting | `pandas.Series.rank` | Highly optimized and handles ties/NaNs correctly. |

## Common Pitfalls

### Pitfall 1: Rate Limiting (HTTP 429)
**What goes wrong:** Yahoo Finance blocks your IP after several hundred requests.
**Why it happens:** Making too many requests in a short window or using a suspicious User-Agent.
**How to avoid:** 
1. Use a real browser `User-Agent`.
2. Use `requests-cache` to reuse data within the same day.
3. Use `yf.download()` for prices (batching) and `yf.Tickers()` for fundamental data.
4. Implement exponential backoff with `tenacity`.

### Pitfall 2: Stale Fundamentals
**What goes wrong:** Fundamental data in `yfinance` can sometimes lag behind official quarterly reports.
**How to avoid:** Compare `yfinance` data with official TWSE data if high precision is needed, but for screening, `yfinance` is usually "good enough."

## Code Examples

### Robust `yfinance` Session
```python
import requests
import requests_cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import yfinance as yf

def get_robust_session():
    # Cache for 24 hours
    session = requests_cache.CachedSession(
        'yfinance_cache',
        expire_after=86400,
        backend='sqlite'
    )
    
    # Custom Headers
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    return session

# Usage
session = get_robust_session()
tickers = yf.Tickers("2330.TW 2317.TW", session=session)
print(tickers.tickers['2330.TW'].info['marketCap'])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `print()` for debugging | `logging` module | Always standard | Better traceability and silent operation in GHA. |
| Manual CSV filtering | Fundamental Screener | 2026 Phase 5 | Automates the "value" filter before technical analysis. |
| Simple Retries | Exponential Backoff | 2026 Phase 5 | Significantly reduces IP blocks from Yahoo. |

## Open Questions

1. **How many tickers can we fetch in one GHA run?**
   - What we know: ~1000 tickers for Taiwan market.
   - What's unclear: If GitHub Actions IPs are more likely to be throttled than local IPs.
   - Recommendation: Start with 10-20 tickers per batch and monitor the 429 error rate.

2. **Weighting of Value Score?**
   - What we know: P/E, P/B, and Yield are standard.
   - What's unclear: If one metric is more predictive in the Taiwan market specifically.
   - Recommendation: Keep weights equal (33.3% each) as a default, but allow user configuration.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ |
| Config file | pytest.ini |
| Quick run command | `pytest tests/unit/` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FUND-01 | Fetch Fundamental Data | integration | `pytest tests/integration/test_fundamentals.py` | ❌ Wave 0 |
| VAL-01 | Calculate Value Score | unit | `pytest tests/unit/test_fundamentals.py` | ❌ Wave 0 |
| REL-01 | Exponential Backoff | unit | `pytest tests/unit/test_session.py` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/unit/test_fundamentals.py` — for Value Score math.
- [ ] `tests/integration/test_fundamentals.py` — for yfinance info fetching.
- [ ] `src/squeeze/core/session.py` — shared robust session implementation.

## Sources

### Primary (HIGH confidence)
- `yfinance` Official Documentation (GitHub) - Checked `Ticker.info` keys.
- Taiwan Stock Exchange (TWSE) Official Website - Verified P/E and Yield calculation standards.
- `tenacity` Documentation - Verified retry patterns.

### Secondary (MEDIUM confidence)
- Community forums (Reddit/StackOverflow) - For `yfinance` rate limit thresholds.
- Investing.com/TradingView - For comparative "Value Score" methodologies.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Libraries are mature.
- Architecture: HIGH - Patterns are standard for Python CLI tools.
- Pitfalls: MEDIUM - Yahoo rate limits are a moving target.

**Research date:** 2026-03-18
**Valid until:** 2026-06-18
