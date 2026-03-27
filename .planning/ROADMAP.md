# Roadmap: Squeeze Stock Screener

## Phase 1: Core Engine & Data (Foundation)
**Goal**: Build the infrastructure to fetch Taiwan stock data and calculate Squeeze indicators.
**Plans:** 3 plans
- [x] 01-01-PLAN.md — Project scaffolding and ISIN ticker discovery.
- [x] 01-02-PLAN.md — Optimized data downloader with caching.
- [x] 01-03-PLAN.md — Refactored indicator engine using pandas-ta.

- [x] 1.1 Project scaffolding (directory structure, dependencies).
- [x] 1.2 Implement Taiwan ticker fetching (TWSE/TPEx).
- [x] 1.3 Implement historical data downloader (optimized for bulk fetching).
- [x] 1.4 Refactor `PowerSqueezeIndicator` from `squeeze.py` into a reusable module.
- [x] 1.5 Unit tests for indicator accuracy.

## Phase 2: Screener & Pattern Logic
**Goal**: Implement the logic to scan the market and identify specific patterns.
**Plans:** 3 plans
- [x] 02-01-PLAN.md — Hybrid Market Scanner and Basic Squeeze logic.
- [x] 02-02-PLAN.md — Houyi Shooting the Sun pattern logic.
- [x] 02-03-PLAN.md — Whale Trading (Daily/Weekly) alignment pattern.

- [x] 2.1 Implement basic Squeeze screener (All stocks currently in Squeeze).
- [x] 2.2 Implement "Houyi Shooting the Sun" pattern detection.
- [x] 2.3 Implement Multi-Timeframe (Daily + Weekly) "Whale Trading" logic.
- [x] 2.4 Performance optimization for full market scan.

## Phase 3: Reporting & Visualization
**Goal**: Generate user-friendly outputs and charts.
**Plans:** 3 plans
- [x] 03-01-PLAN.md — Implement CSV/JSON/MD report generation.
- [x] 03-02-PLAN.md — Implement automated chart generation for top picks.
- [x] 03-03-PLAN.md — CLI integration for exports and plotting.

- [x] 3.1 Implement CSV/JSON report generation.
- [x] 3.2 Implement automated chart generation for top picks using `mplfinance`.
- [x] 3.3 Create a CLI command to run specific screens (e.g., `--pattern houyi`).

## Phase 4: Automation & Deployment
**Goal**: Set up scheduled runs and historical tracking.
**Plans:** 2 plans
- [x] 04-01-PLAN.md — Notification logic and CLI enhancements.
- [x] 04-02-PLAN.md — GitHub Actions and Integration testing.

- [x] 4.1 Configure GitHub Actions workflow for daily execution.
- [x] 4.2 Implement historical result persistence.
- [x] 4.3 Integration with Line Bot for notifications (from Phase 3 logic).

## Phase 5: Refinement & Fundamentals
**Goal**: Add advanced filtering and improve reliability for v1.0.
**Plans:** 4 plans
- [x] 05-01-PLAN.md — Reliability & Fundamentals Data.
- [x] 05-02-PLAN.md — Ranking Logic & Integration.
- [x] 05-03-PLAN.md — CLI Filters & Integration Tests.
- [x] 05-04-PLAN.md — Documentation & Polish.

- [x] 5.1 Integrate fundamental data filtering (e.g., volume thresholds, price filters).
- [x] 5.2 Improve error handling and retry logic for data providers.
- [x] 5.3 Final documentation and user guide.
