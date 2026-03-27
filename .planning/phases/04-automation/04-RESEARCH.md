# Phase 4: Automation & Deployment - Research

**Researched:** 2026-03-18
**Domain:** DevOps, Automation, Messaging APIs
**Confidence:** HIGH

## Summary
The primary strategy for Phase 4 is a GitHub Actions workflow that executes a daily scan, commits results to the repository for historical tracking, and sends a summary notification via the LINE Messaging API.

**Primary recommendation:** Use `stefanzweifel/git-auto-commit-action` for persistence and `line-bot-sdk` v3 for notifications, triggered by a cron job at `07:30 UTC` (15:30 TST).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `line-bot-sdk` | v3.0+ | Messaging API | Official SDK for LINE integration. |
| `stefanzweifel/git-auto-commit-action` | v5 | Git Persistence | Standard for pushing changes back to the repo. |
| `actions/checkout` | v4 | Repo access | Standard for CI/CD checkout. |

## Architecture Patterns

### Recommended Project Structure
```
exports/
└── YYYY-MM-DD/
    ├── scan_summary_*.md   # Human readable summary
    ├── scan_results_*.csv  # Raw data
    └── charts/             # .png files
.github/
└── workflows/
    └── daily_scan.yml      # The automation pipeline
```

### Pattern 1: Scheduled Execution
**Cron Syntax for 15:30 TST:** `30 7 * * 1-5` (Mon-Fri).

### Pattern 2: Secret Management
- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`

## Metadata
**Research date:** 2026-03-18
**Valid until:** 2026-06-18
