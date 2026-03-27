# Requirements: Squeeze Stock Screener

## 1. Functional Requirements

### 1.1 Data Acquisition
- **TW Stock Tickers**: The system must maintain or dynamically fetch a list of all TWSE and TPEx stock tickers.
- **Historical Data**: For each ticker, the system must fetch at least 6 months of daily OHLC (Open, High, Low, Close) data.
- **Multi-Timeframe Support**: Capability to fetch Weekly data for "Whale Trading" pattern confirmation.

### 1.2 Technical Analysis (Squeeze Logic)
- **Bollinger Bands (BB)**: Calculate standard 20-period BB with 2.0 standard deviations.
- **Keltner Channels (KC)**: Calculate 20-period KC using a 1.5x ATR multiplier.
- **Squeeze Detection**: Identify "Squeeze" state when BB is fully contained within KC.
- **Momentum Histogram**: Calculate momentum (e.g., linear regression of price or MACD-like histogram) to determine the Squeeze direction.
- **Pattern Recognition**:
    - **Houyi Shooting the Sun**: Detect strong rallies followed by a 50%-61.8% retracement into a Squeeze consolidation.
    - **Whale Trading**: Confirm Squeeze on both Daily and Weekly timeframes.

### 1.3 Screening & Reporting
- **Filtering**: Filter stocks based on specific Squeeze states (e.g., "Squeeze On", "Squeeze Fired").
- **Visual Output**: Generate `.png` charts for the top identified stocks, highlighting the Squeeze and breakout signals.
- **Summary Report**: Export a text/CSV report of all screened stocks with their metrics.

### 1.4 Automation
- **Scheduled Execution**: Integration with GitHub Actions to run the screen daily (e.g., after market close at 15:00 TST).
- **Persistence**: Save results to a directory (e.g., `results/YYYY-MM-DD/`) for historical tracking.

## 2. Non-Functional Requirements

### 2.1 Performance
- **Parallel Processing**: Use multi-threading or async I/O to fetch data for 1000+ tickers efficiently.
- **Execution Time**: The full market scan should complete within 30 minutes.

### 2.2 Reliability
- **Error Handling**: Gracefully handle missing data or API rate limits from `yfinance`.
- **Validation**: Ensure data integrity before performing calculations.

### 2.3 Maintainability
- **Modularity**: Separation of data fetching, technical analysis, and reporting logic.
- **Testing**: Unit tests for technical indicator calculations.

## 3. Future Scope
- Integration with Line Bot for instant mobile notifications.
- Fundamental data filtering (e.g., Growin Value Score).
