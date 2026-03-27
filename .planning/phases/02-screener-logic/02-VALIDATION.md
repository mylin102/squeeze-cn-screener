# Phase 2 Validation: Screener & Pattern Logic

## 1. Requirement Coverage

| ID | Description | Plan | Status |
|----|-------------|------|--------|
| 2.1 | Basic Squeeze screener (All stocks in Squeeze) | 02-01 | Pending |
| 2.2 | "Houyi Shooting the Sun" pattern detection | 02-02 | Pending |
| 2.3 | Multi-Timeframe (Daily + Weekly) "Whale Trading" logic | 02-03 | Pending |
| 2.4 | Performance optimization for full market scan (Hybrid approach) | 02-01 | Pending |

## 2. Automated Verification

| Wave | Command | Target | Purpose |
|------|---------|--------|---------|
| 1 | `pytest tests/integration/test_scanner.py` | Scanner | Verify hybrid thread/multiprocessing throughput |
| 2 | `pytest tests/unit/test_patterns.py -k houyi` | Patterns | Verify Houyi detection accuracy with synthetic data |
| 3 | `pytest tests/unit/test_patterns.py -k whale` | Patterns | Verify Whale Trading (Daily+Weekly) alignment |
| 3 | `python3 -m squeeze scan --pattern whale --limit 10` | CLI | E2E verification of advanced pattern scanning |

## 3. Critical Checkpoints

### 3.1 Scanner Performance
- [ ] 1000+ tickers analyzed in under 5 minutes (I/O + CPU).
- [ ] Multiprocessing worker pool correctly utilizes available CPU cores.

### 3.2 Pattern Accuracy
- [ ] Houyi: Correctly identifies "Bow Line" (Upper Wick >= 2x Body) and 0.5-0.618 Fib zone.
- [ ] Whale: Correctly resamples Daily data to Weekly for consistent MTF alignment.
- [ ] Whale: Signals only when both Daily and Weekly timeframes are in a Squeeze.

### 3.3 CLI Usability
- [ ] `scan` command supports `--pattern` (squeeze, houyi, whale).
- [ ] `scan` command provides progress feedback (e.g., via `rich`).
