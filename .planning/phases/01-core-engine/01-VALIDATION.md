# Phase 1 Validation: Core Engine & Data

## 1. Requirement Coverage

| ID | Description | Plan | Status |
|----|-------------|------|--------|
| 1.1 | Project scaffolding (src layout, pyproject.toml) | 01-01 | Pending |
| 1.2 | Taiwan ticker fetching (TWSE/TPEx from ISIN) | 01-01 | Pending |
| 1.3 | Historical data downloader (Bulk yfinance) | 01-02 | Pending |
| 1.4 | Refactor Indicator logic to pandas-ta | 01-03 | Pending |
| 1.5 | Unit tests for indicator accuracy | 01-03 | Pending |

## 2. Automated Verification

| Wave | Command | Target | Purpose |
|------|---------|--------|---------|
| 1 | `python -m squeeze --help` | CLI | Verify project install & CLI structure |
| 1 | `pytest tests/integration/test_tickers.py` | Tickers | Verify ISIN scraper connectivity |
| 2 | `pytest tests/integration/test_download.py` | Data | Verify yfinance bulk downloader |
| 3 | `pytest tests/unit/test_indicators.py` | Engine | Verify Squeeze calculation accuracy |

## 3. Critical Checkpoints

### 3.1 Project Layout
- [ ] `src/squeeze/` exists with `__main__.py` and `cli.py`.
- [ ] `pyproject.toml` contains all dependencies (`pandas-ta`, `yfinance`, `typer`).

### 3.2 Ticker Source
- [ ] Scraper handles both `strMode=2` (Listed) and `strMode=4` (OTC).
- [ ] Tickers are mapped to Yahoo symbols (e.g., `2330.TW`, `8069.TWO`).

### 3.3 Indicator Logic
- [ ] Bollinger Bands (20, 2.0) match pandas-ta standard.
- [ ] Keltner Channels (20, 1.5) match pandas-ta standard.
- [ ] Squeeze state (ON/OFF) is correctly derived from BB/KC relationship.
