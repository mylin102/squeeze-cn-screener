# Phase 3 Validation: Reporting & Visualization

## 1. Requirement Coverage

| ID | Description | Plan | Status |
|----|-------------|------|--------|
| 3.1 | Implement CSV/JSON report generation | 03-01 | Pending |
| 3.2 | Implement automated chart generation for top picks | 03-02 | Pending |
| 3.3 | Create a CLI command to run specific screens | 03-03 | Pending |

## 2. Automated Verification

| Wave | Command | Target | Purpose |
|------|---------|--------|---------|
| 1 | `pytest tests/unit/test_exporter.py` | Exporter | Verify CSV/JSON/MD file generation |
| 1 | `pytest tests/integration/test_visualizer.py` | Visualizer | Verify mplfinance chart creation |
| 2 | `pytest tests/integration/test_cli_reporting.py` | CLI | Verify export/plot flags |
| 2 | `python3 -m squeeze scan --limit 5 --export csv --plot --top 2` | E2E | End-to-end reporting flow |

## 3. Critical Checkpoints

### 3.1 Exporter
- [ ] `exports/YYYY-MM-DD/results.csv` contains all scanned stock results.
- [ ] `exports/YYYY-MM-DD/state.json` contains run metadata (timestamp, tickers scanned).
- [ ] `exports/YYYY-MM-DD/summary.md` is generated using Jinja2 and contains a summary table.

### 3.2 Visualizer
- [ ] Charts are saved as `.png` in `exports/YYYY-MM-DD/charts/`.
- [ ] Charts show candlesticks, BB (dashed), KC (solid), and Squeeze dots.
- [ ] Charts include a momentum histogram panel.

### 3.3 CLI Integration
- [ ] `--export` flag correctly triggers file generation.
- [ ] `--plot` flag correctly triggers chart generation.
- [ ] `--top` flag limits the number of charts generated to avoid overhead.
