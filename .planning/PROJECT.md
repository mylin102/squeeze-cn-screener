# Project: Squeeze Stock Screener (Taiwan Market)

## Overview
A Python-based CLI tool designed to identify high-potential trading entries in the Taiwan Stock Market using the "Squeeze" indicator logic (Bollinger Bands vs. Keltner Channels).

## Vision
To automate the process of finding stocks in an energy-accumulation phase (Squeeze) and detecting the early stages of a momentum breakout, specifically targeting the "Houyi Shooting the Sun" pattern or "Whale Trading" opportunities.

## Core Features
- **Squeeze Detection**: Calculate and identify stocks where Bollinger Bands are within Keltner Channels.
- **Momentum Analysis**: Monitor the histogram to determine the direction of the energy release.
- **Taiwan Market Coverage**: Support for TWSE and TPEx stocks.
- **Daily Automation**: Scheduled execution to scan the market daily.
- **Notification System**: (Implied) Report findings to the user.

## Tech Stack
- **Language**: Python 3.x
- **Data Sources**: `yfinance` or local market data APIs.
- **Analysis**: `pandas`, `numpy`.
- **Visualization**: `matplotlib` (for generating charts of potential picks).
- **Automation**: GitHub Actions.

## Context from Workspace
The project will leverage existing logic found in `squeeze.py` and `squeeze.md` to build a robust, production-grade screener.
