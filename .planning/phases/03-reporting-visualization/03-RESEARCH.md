# Phase 3: Reporting & Visualization - Research

**Researched:** 2026-03-18
**Domain:** Financial Reporting and Plotting
**Confidence:** HIGH

## Summary

Phase 3 focuses on transforming the raw scan results into actionable intelligence for traders. This involves two main components: structured text/data reports (CSV, JSON, Markdown) and visual analysis (automated chart generation).

The primary recommendation is to use `mplfinance` for chart generation due to its native handling of OHLCV data and built-in support for overlays like Bollinger Bands and Keltner Channels. For reporting, a tiered approach is proposed: CSV for data analysts, JSON for automated state persistence, and Markdown for human-readable summaries (perfect for GitHub Actions or messaging apps).

**Primary recommendation:** Use `mplfinance` for high-fidelity trading charts and a tiered file structure under `exports/YYYY-MM-DD/` for all outputs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Standard technical indicator library: `pandas_ta`
- Main CLI framework: `typer`
- Market data source: `yfinance`

### Claude's Discretion
- Choice of plotting library (`matplotlib` or `mplfinance`)
- Exact reporting schema and file structure
- Logic for selecting "top picks" for chart generation

### Deferred Ideas (OUT OF SCOPE)
- Real-time trading execution (Phase 5+)
- Full-blown web dashboard (Phase 4 may add static HTML)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| 3.1 | Implement CSV/JSON report generation | Standardized schemas for CSV (flat) and JSON (metadata) |
| 3.2 | Implement automated chart generation for top picks | `mplfinance` with `make_addplot` for Squeeze overlays |
| 3.3 | Create a CLI command to run specific screens | Enhanced `squeeze scan` with export flags |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `mplfinance` | 0.12.10 | Financial plotting | Native OHLCV support, built-in paneling, and overlays. |
| `pandas` | ^2.1.0 | Data manipulation | Industry standard for financial time series. |
| `jinja2` | ^3.1.2 | Markdown templating | Allows for clean, reusable report templates. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `pathlib` | (stdlib) | Path management | Organizing export directories safely. |
| `json` | (stdlib) | Metadata storage | Storing run parameters and execution time. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `mplfinance` | `plotly` | Interactive but harder to generate static files for CLI/CI. |
| `mplfinance` | `matplotlib` (raw) | Requires writing significant boilerplate for candlestick logic. |

**Installation:**
```bash
pip install mplfinance jinja2
```

**Version verification:** 
- `mplfinance`: 0.12.10 (Verified March 2026)
- `jinja2`: 3.1.3 (Verified March 2026)

## Architecture Patterns

### Recommended Project Structure
```
src/
└── squeeze/
    ├── exports/             # Base directory for outputs (created on demand)
    │   └── YYYY-MM-DD/      # Daily subdirectories
    │       ├── charts/      # PNG files for top picks
    │       ├── summary.md   # Human-readable report
    │       ├── results.csv  # Full scan data
    │       └── state.json   # Run metadata
    └── reporter/            # New module for Phase 3
        ├── __init__.py
        ├── charts.py        # mplfinance logic
        └── formats.py       # CSV/JSON/MD generators
```

### Pattern 1: Multi-Format Reporting
**What:** Decouple analysis from output generation. The scanner produces a `List[Dict]`, which the `Reporter` converts into multiple formats.
**When to use:** Whenever running a full market scan.
**Example:**
```python
# Pseudo-code for reporter coordination
class Reporter:
    def export_all(self, results: List[Dict], output_dir: Path):
        self.to_csv(results, output_dir / "results.csv")
        self.to_json(results, output_dir / "state.json")
        self.to_markdown(results, output_dir / "summary.md")
        self.generate_top_charts(results, output_dir / "charts")
```

### Pattern 2: Squeeze Chart Overlay
**What:** Using `mpf.make_addplot` to overlay Bollinger Bands (dashed), Keltner Channels (solid), and Squeeze dots (colored scatters).
**When to use:** Generating "Top Picks" visualizations.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chart Generation | Custom Matplotlib candle logic | `mplfinance` | Handles gaps (weekends), time axis, and panels automatically. |
| Report Templates | Complex f-string concatenation | `Jinja2` | Easier to maintain complex Markdown tables and conditional formatting. |
| Path Management | String manipulation (`"/" + ...`) | `pathlib` | Cross-platform compatibility and robust directory creation. |

## Common Pitfalls

### Pitfall 1: Non-Trading Days (Time Gaps)
**What goes wrong:** Charts look stretched or broken on weekends/holidays.
**How to avoid:** Use `show_nontrading=False` in `mplfinance` (default).

### Pitfall 2: Memory Leak with Many Plots
**What goes wrong:** Generating 100+ charts in a single CLI run consumes all RAM.
**How to avoid:** Explicitly close the figures: `import matplotlib.pyplot as plt; plt.close('all')`.

### Pitfall 3: Relative Paths in Exports
**What goes wrong:** Exports end up in the user's home or current working directory instead of the project root.
**How to avoid:** Use `Path(__file__).parent.parent` or a configurable `--export-dir` flag with an absolute path fallback.

## Code Examples

### Professional Squeeze Chart with `mplfinance`
```python
import mplfinance as mpf

def plot_squeeze(df, ticker, output_path):
    # Overlay 1: Bollinger Bands
    # Overlay 2: Keltner Channels
    # Overlay 3: Squeeze Dots (Red/Green)
    # Subplot 2: Momentum Histogram
    
    apds = [
        mpf.make_addplot(df['BB_upper'], color='blue', linestyle='dashed'),
        mpf.make_addplot(df['BB_lower'], color='blue', linestyle='dashed'),
        mpf.make_addplot(df['KC_upper'], color='orange'),
        mpf.make_addplot(df['KC_lower'], color='orange'),
        mpf.make_addplot(df['Squeeze_Dots'], type='scatter', color='red', markersize=20, panel=1),
        mpf.make_addplot(df['Momentum'], type='bar', color='gray', panel=1, alpha=0.5)
    ]
    
    mpf.plot(df, type='candle', addplot=apds, savefig=output_path, 
             title=f"{ticker} Squeeze Analysis", volume=True, panel_ratios=(6,2))
```

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Custom SVG charts | `mplfinance` / `plotly` | Faster development, higher fidelity. |
| Flat text logs | Markdown summaries | Beautiful integration with GitHub Actions / CI. |

## Open Questions

1. **How many charts should we generate by default?**
   - Recommendation: 10-15 top picks to keep runtime and storage reasonable.
2. **Should we include "Historical Accuracy" in the report?**
   - What we know: We have data to check if past squeezes fired successfully.
   - What's unclear: It adds significant complexity to the report generator.
   - Recommendation: Defer to Phase 4 (Historical Tracking).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/unit/` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-3.1 | CSV/JSON creation | unit | `pytest tests/unit/test_reporter.py` | ❌ Wave 0 |
| REQ-3.2 | Chart file generation | integration | `pytest tests/integration/test_plotting.py` | ❌ Wave 0 |
| REQ-3.3 | CLI flags working | integration | `pytest tests/integration/test_cli_reporting.py` | ❌ Wave 0 |

### Wave 0 Gaps
- [ ] `tests/unit/test_reporter.py` — Verifies reporting logic.
- [ ] `tests/integration/test_plotting.py` — Verifies chart generation doesn't crash and saves files.
- [ ] Framework install: `pip install mplfinance jinja2`

## Sources

### Primary (HIGH confidence)
- `mplfinance` official documentation: Overlay and Addplot examples.
- `pandas-ta` TTM Squeeze implementation details.

### Secondary (MEDIUM confidence)
- "Best practices for financial reporting in Python" - community articles.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - `mplfinance` is the industry standard for Python financial plotting.
- Architecture: HIGH - Tiered reporting is a proven pattern in screener apps.
- Pitfalls: MEDIUM - Memory management needs validation during implementation.

**Research date:** 2026-03-18
**Valid until:** 2026-06-18
