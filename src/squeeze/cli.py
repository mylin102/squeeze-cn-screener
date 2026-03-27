import typer
import pandas as pd
import json
from rich.console import Console
from rich.table import Table
from pathlib import Path

from typing import Optional

from squeeze.data.tickers import fetch_tickers_with_names
from squeeze.data.downloader import download_market_data
from squeeze.report.backtest import (
    export_backtest_report,
    export_rolling_backtest_report,
    render_backtest_grid_report,
    render_backtest_report,
    render_rolling_backtest_report,
    run_rolling_backtest,
    run_signal_backtest,
)
from squeeze.report.exporter import ReportExporter
from squeeze.report.notifier import LineNotifier, EmailNotifier
from squeeze.report.performance import PerformanceTracker
from squeeze.report.tracking_analysis import build_tracking_report, format_tracking_report, load_tracking_frame

app = typer.Typer(help="Squeeze CN Screener for China Market")
console = Console()


def _signal_score(signal: str) -> int:
    if signal == "強烈買入 (爆發)":
        return 3
    if signal == "買入 (動能增強)":
        return 2
    if signal == "觀察 (跌勢收斂)":
        return 1
    return 0


def _attach_pattern_flags(results, houyi_results, whale_results):
    houyi_map = {r["ticker"]: r for r in houyi_results if r.get("is_houyi")}
    whale_map = {r["ticker"]: r for r in whale_results if r.get("is_whale")}
    enriched = []
    for result in results:
        ticker = result.get("ticker")
        has_houyi = ticker in houyi_map
        has_whale = ticker in whale_map
        enriched_result = dict(result)
        enriched_result["has_houyi"] = has_houyi
        enriched_result["has_whale"] = has_whale
        enriched_result["composite_score"] = _signal_score(result.get("Signal", "")) + (1 if has_houyi else 0) + (2 if has_whale else 0)
        enriched.append(enriched_result)
    return enriched


def _safe_chart_stem(ticker: str, name: str) -> str:
    base = f"{ticker.split('.')[0]}_{name or 'unknown'}"
    for char in '/\\:*?"<>|':
        base = base.replace(char, "_")
    return base.strip().replace(" ", "_")


def _normalize_cn_ticker(raw_ticker: str, ticker_map: dict[str, str]) -> str:
    ticker = raw_ticker.strip().upper()
    if ticker in ticker_map:
        return ticker

    if "." in ticker:
        return ticker

    if ticker.isdigit():
        for suffix in (".SZ", ".SS"):
            candidate = f"{ticker}{suffix}"
            if candidate in ticker_map:
                return candidate

    return ticker


@app.command(name="analyze-tracking")
def analyze_tracking(
    csv_path: Path = typer.Option(Path("recommendations.csv"), "--csv", help="Tracking CSV to analyze."),
):
    """Analyze completed tracking history and summarize strategy health."""
    report = build_tracking_report(load_tracking_frame(str(csv_path)))
    console.print(format_tracking_report(report))


@app.command(name="backtest")
def backtest(
    start: str = typer.Option("2026-01-01", "--start", help="Backtest start date (YYYY-MM-DD)."),
    end: Optional[str] = typer.Option(None, "--end", help="Backtest end date (YYYY-MM-DD). Defaults to today."),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit tickers for quick validation runs."),
    max_positions: int = typer.Option(10, "--max-positions", help="Maximum simultaneous positions."),
    initial_capital: float = typer.Option(1_000_000.0, "--initial-capital", help="Initial portfolio capital."),
    stop_loss_ma_window: Optional[int] = typer.Option(None, "--stop-loss-ma-window", help="Exit when close falls below the moving average window by the configured ticks."),
    stop_loss_ticks: int = typer.Option(0, "--stop-loss-ticks", help="Number of price ticks below the moving average to trigger stop loss."),
    stop_loss_pct: Optional[float] = typer.Option(None, "--stop-loss-pct", help="Exit when close falls by this percentage below entry price."),
    transaction_cost_bps: float = typer.Option(0.0, "--transaction-cost-bps", help="Transaction cost in basis points applied on both entry and exit."),
    slippage_bps: float = typer.Option(0.0, "--slippage-bps", help="Slippage in basis points applied on both entry and exit."),
    include_observation: bool = typer.Option(True, "--include-observation/--exclude-observation", help="Include or exclude '觀察 (跌勢收斂)' buy signals."),
    rolling_window_sessions: Optional[int] = typer.Option(None, "--rolling-window-sessions", help="Run rolling stability analysis using this many trading sessions per window."),
    rolling_step_sessions: int = typer.Option(10, "--rolling-step-sessions", help="Advance rolling windows by this many trading sessions."),
    cache_path: Optional[Path] = typer.Option(None, "--cache-path", help="Read and write historical price cache from this pickle path."),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Ignore existing cache and rebuild it from live data."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Output directory for reports."),
):
    """Backtest buy and sell signals using historical daily data."""
    console.print("[yellow]Preparing backtest universe...[/yellow]")
    ticker_map = fetch_tickers_with_names()
    all_tickers = sorted(ticker_map.keys())
    if limit:
        all_tickers = all_tickers[:limit]
        console.print(f"[yellow]Limiting backtest to {limit} tickers.[/yellow]")

    console.print(f"[green]Downloading historical data for {len(all_tickers)} tickers...[/green]")
    with console.status("[bold green]Fetching price history...[/bold green]"):
        price_data = download_market_data(
            all_tickers,
            period="1y",
            cache_path=cache_path,
            refresh_cache=refresh_cache,
        )

    if price_data.empty:
        console.print("[red]No historical data available for backtest.[/red]")
        raise typer.Exit(code=1)

    selected_buy_signals = {"強烈買入 (爆發)", "買入 (動能增強)"}
    if include_observation:
        selected_buy_signals.add("觀察 (跌勢收斂)")
    base_dir = output_dir or Path("exports") / "backtests"
    if rolling_window_sessions:
        console.print("[yellow]Running rolling backtest analysis...[/yellow]")
        report = run_rolling_backtest(
            price_data=price_data,
            ticker_names=ticker_map,
            start_date=start,
            end_date=end,
            initial_capital=initial_capital,
            max_positions=max_positions,
            stop_loss_ma_window=stop_loss_ma_window,
            stop_loss_ticks=stop_loss_ticks,
            stop_loss_pct=stop_loss_pct,
            buy_signals=selected_buy_signals,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
            rolling_window_sessions=rolling_window_sessions,
            rolling_step_sessions=rolling_step_sessions,
        )
        paths = export_rolling_backtest_report(report, base_dir / "rolling")
        console.print(render_rolling_backtest_report(report))
    else:
        console.print("[yellow]Running signal backtest...[/yellow]")
        report = run_signal_backtest(
            price_data=price_data,
            ticker_names=ticker_map,
            start_date=start,
            end_date=end,
            initial_capital=initial_capital,
            max_positions=max_positions,
            stop_loss_ma_window=stop_loss_ma_window,
            stop_loss_ticks=stop_loss_ticks,
            stop_loss_pct=stop_loss_pct,
            buy_signals=selected_buy_signals,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
        )
        paths = export_backtest_report(report, base_dir)
        console.print(render_backtest_report(report))

    console.print(f"[green]Saved markdown report:[/green] {paths['markdown']}")
    console.print(f"[green]Saved JSON report:[/green] {paths['json']}")


@app.command(name="backtest-grid")
def backtest_grid(
    start: str = typer.Option("2026-01-01", "--start", help="Backtest start date (YYYY-MM-DD)."),
    end: Optional[str] = typer.Option(None, "--end", help="Backtest end date (YYYY-MM-DD). Defaults to today."),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit tickers for quick validation runs."),
    max_positions: int = typer.Option(10, "--max-positions", help="Maximum simultaneous positions."),
    initial_capital: float = typer.Option(1_000_000.0, "--initial-capital", help="Initial portfolio capital."),
    ma_windows: str = typer.Option("20,30", "--ma-windows", help="Comma-separated MA windows to test."),
    ticks: str = typer.Option("1,2,3", "--ticks", help="Comma-separated tick offsets to test."),
    cache_path: Optional[Path] = typer.Option(None, "--cache-path", help="Read and write historical price cache from this pickle path."),
    refresh_cache: bool = typer.Option(False, "--refresh-cache", help="Ignore existing cache and rebuild it from live data."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Output directory for grid reports."),
):
    """Run a stop-loss parameter grid for signal backtests."""
    console.print("[yellow]Preparing backtest grid universe...[/yellow]")
    ticker_map = fetch_tickers_with_names()
    all_tickers = sorted(ticker_map.keys())
    if limit:
        all_tickers = all_tickers[:limit]
        console.print(f"[yellow]Limiting backtest grid to {limit} tickers.[/yellow]")

    ma_values = [int(item.strip()) for item in ma_windows.split(",") if item.strip()]
    tick_values = [int(item.strip()) for item in ticks.split(",") if item.strip()]
    if not ma_values or not tick_values:
        console.print("[red]MA windows and ticks must not be empty.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]Downloading historical data for {len(all_tickers)} tickers...[/green]")
    with console.status("[bold green]Fetching price history...[/bold green]"):
        price_data = download_market_data(
            all_tickers,
            period="1y",
            cache_path=cache_path,
            refresh_cache=refresh_cache,
        )

    if price_data.empty:
        console.print("[red]No historical data available for backtest grid.[/red]")
        raise typer.Exit(code=1)

    rows = []
    for ma_window in ma_values:
        for tick_value in tick_values:
            console.print(f"[yellow]Testing MA {ma_window} / ticks {tick_value}...[/yellow]")
            report = run_signal_backtest(
                price_data=price_data,
                ticker_names=ticker_map,
                start_date=start,
                end_date=end,
                initial_capital=initial_capital,
                max_positions=max_positions,
                stop_loss_ma_window=ma_window,
                stop_loss_ticks=tick_value,
            )
            summary = report["summary"]
            rows.append(
                {
                    "ma_window": ma_window,
                    "ticks": tick_value,
                    "ending_equity": summary["ending_equity"],
                    "total_return_pct": summary["total_return_pct"],
                    "max_drawdown_pct": summary["max_drawdown_pct"],
                    "sharpe_ratio": summary["sharpe_ratio"],
                    "win_rate_pct": summary["win_rate_pct"],
                    "avg_trade_return_pct": summary["avg_trade_return_pct"],
                    "profit_factor": summary["profit_factor"],
                }
            )

    rows = sorted(rows, key=lambda item: (item["total_return_pct"], item["sharpe_ratio"]), reverse=True)
    report_text = render_backtest_grid_report(rows, start, end or pd.Timestamp.now().strftime("%Y-%m-%d"))
    console.print(report_text)

    base_dir = output_dir or Path("exports") / "backtests" / "grid"
    base_dir.mkdir(parents=True, exist_ok=True)
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    md_path = base_dir / f"backtest_grid_{timestamp}.md"
    json_path = base_dir / f"backtest_grid_{timestamp}.json"
    md_path.write_text(report_text, encoding="utf-8")
    json_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    console.print(f"[green]Saved markdown report:[/green] {md_path}")
    console.print(f"[green]Saved JSON report:[/green] {json_path}")


@app.command(name="analyze")
def analyze(
    ticker: str = typer.Option(..., "--ticker", help="Single China ticker to analyze."),
    pattern: str = typer.Option("squeeze", "--pattern", "-P", help="Pattern to analyze (squeeze, houyi, whale)"),
    period: str = typer.Option("2y", "--period", "-p", help="Data period (e.g., 2y, 1y, 6mo)"),
    fundamentals: bool = typer.Option(True, "--fundamentals/--no-fundamentals", help="Include fundamentals if available."),
):
    """Analyze a single China ticker and print the latest pattern state."""
    from squeeze.engine.patterns import detect_squeeze, detect_houyi_shooting_sun, detect_whale_trading
    from squeeze.engine.scanner import MarketScanner

    pattern_map = {
        "squeeze": ("Squeeze", detect_squeeze),
        "houyi": ("Houyi Shooting the Sun", detect_houyi_shooting_sun),
        "whale": ("Whale Trading", detect_whale_trading),
    }

    if pattern not in pattern_map:
        console.print(f"[red]Unknown pattern: {pattern}.[/red]")
        raise typer.Exit(code=1)

    pattern_title, pattern_fn = pattern_map[pattern]
    ticker_map = fetch_tickers_with_names()
    normalized_ticker = _normalize_cn_ticker(ticker, ticker_map)
    scanner = MarketScanner([normalized_ticker], ticker_names=ticker_map)

    with console.status(f"[bold green]Downloading market data for {normalized_ticker}...[/bold green]"):
        scanner.fetch_data(period=period)

    if scanner.data.empty:
        console.print(f"[red]No market data available for {normalized_ticker}.[/red]")
        raise typer.Exit(code=1)

    if fundamentals:
        with console.status(f"[bold green]Fetching fundamentals for {normalized_ticker}...[/bold green]"):
            scanner.fetch_fundamentals()

    results = scanner.scan(pattern_fn)
    if not results:
        console.print(f"[red]No analysis result produced for {normalized_ticker}.[/red]")
        raise typer.Exit(code=1)

    result = results[0]
    table = Table(title=f"{pattern_title} Analysis: {normalized_ticker}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    display_rows = [
        ("Ticker", result.get("ticker", normalized_ticker)),
        ("Name", result.get("name", ticker_map.get(normalized_ticker, "未知"))),
        ("Signal", result.get("Signal", "觀望")),
        ("Close", f"{result.get('Close', 0.0):.2f}" if result.get("Close") is not None else "N/A"),
        ("Squeeze On", "Yes" if result.get("squeeze_on") else "No"),
        ("Fired", "Yes" if result.get("fired") else "No"),
        ("Energy Level", str(result.get("energy_level", 0))),
        ("Momentum", f"{result.get('momentum', 0.0):.4f}"),
        ("Prev Momentum", f"{result.get('prev_momentum', 0.0):.4f}"),
    ]

    if pattern == "houyi":
        display_rows.extend([
            ("Houyi Match", "Yes" if result.get("is_houyi") else "No"),
            ("Rally %", f"{result.get('rally_pct', 0.0):.2%}"),
            ("Fib Level", f"{result.get('fib_level', 0.0):.3f}"),
            ("Shooting Star", "Yes" if result.get("shooting_star") else "No"),
        ])
    elif pattern == "whale":
        display_rows.extend([
            ("Whale Match", "Yes" if result.get("is_whale") else "No"),
            ("Daily Squeeze", "Yes" if result.get("daily_squeeze") else "No"),
            ("Weekly Squeeze", "Yes" if result.get("weekly_squeeze") else "No"),
            ("Daily Momentum", f"{result.get('daily_momentum', 0.0):.4f}"),
            ("Weekly Momentum", f"{result.get('weekly_momentum', 0.0):.4f}"),
        ])
    else:
        display_rows.extend([
            ("Squeeze Match", "Yes" if (result.get("is_squeezed") or result.get("fired")) else "No"),
            ("Timestamp", result.get("timestamp", "N/A")),
        ])

    fundamentals_map = {
        "marketCap": "Market Cap",
        "averageVolume": "Average Volume",
        "trailingPE": "Trailing PE",
        "priceToBook": "Price/Book",
        "dividendYield": "Dividend Yield",
        "value_score": "Value Score",
    }
    for key, label in fundamentals_map.items():
        if key in result and pd.notna(result[key]):
            value = result[key]
            if key == "marketCap":
                value = f"{float(value) / 1e9:.2f}B"
            elif key == "dividendYield":
                value = f"{float(value):.2%}"
            elif isinstance(value, float):
                value = f"{value:.2f}"
            display_rows.append((label, str(value)))

    for field, value in display_rows:
        table.add_row(field, value)

    console.print(table)


@app.command(name="plot")
def plot(
    ticker: str = typer.Option(..., "--ticker", help="Single China ticker to plot."),
    period: str = typer.Option("2y", "--period", "-p", help="Data period (e.g., 2y, 1y, 6mo)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output PNG path."),
):
    """Generate a chart for a single China ticker."""
    from squeeze.engine.scanner import MarketScanner
    from squeeze.report.visualizer import plot_ticker

    ticker_map = fetch_tickers_with_names()
    normalized_ticker = _normalize_cn_ticker(ticker, ticker_map)
    scanner = MarketScanner([normalized_ticker], ticker_names=ticker_map)

    with console.status(f"[bold green]Downloading market data for {normalized_ticker}...[/bold green]"):
        scanner.fetch_data(period=period)

    if scanner.data.empty:
        console.print(f"[red]No market data available for {normalized_ticker}.[/red]")
        raise typer.Exit(code=1)

    if isinstance(scanner.data.columns, pd.MultiIndex):
        ticker_df = scanner.data[normalized_ticker].dropna(subset=["Close"])
    else:
        ticker_df = scanner.data.dropna(subset=["Close"])

    if ticker_df.empty:
        console.print(f"[red]No plottable data available for {normalized_ticker}.[/red]")
        raise typer.Exit(code=1)

    display_name = ticker_map.get(normalized_ticker, "未知")
    safe_name = _safe_chart_stem(normalized_ticker, display_name)
    chart_path = output or Path("exports") / "single" / f"{safe_name}.png"
    plot_ticker(ticker_df, f"{normalized_ticker} {display_name}", str(chart_path))
    console.print(f"[green]Saved chart:[/green] {chart_path}")

@app.command(name="scan")
def scan(
    pattern: str = typer.Option("squeeze", "--pattern", "-P", help="Pattern to scan for (squeeze, houyi, whale)"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit the number of tickers to scan (for testing)"),
    period: str = typer.Option("2y", "--period", "-p", help="Data period (e.g., 2y, 1y, 6mo)"),
    export: bool = typer.Option(False, "--export", "-e", help="Export results to CSV/JSON/MD"),
    plot: bool = typer.Option(False, "--plot", help="Generate charts for top picks"),
    top: int = typer.Option(10, "--top", help="Number of top picks to plot"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Output directory for reports and charts"),
    notify: bool = typer.Option(False, "--notify", help="Send notification summary (e.g., via LINE)"),
    min_mkt_cap: Optional[float] = typer.Option(None, "--min-mkt-cap", help="Minimum market capitalization (in billion CNY)"),
    min_volume: Optional[float] = typer.Option(None, "--min-volume", help="Minimum average daily volume"),
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Minimum Value Score (0.0 - 1.0)"),
    min_price: Optional[float] = typer.Option(None, "--min-price", help="Minimum stock price (CNY)"),
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Maximum stock price (CNY)"),
    tracking_stop_loss_pct: Optional[float] = typer.Option(None, "--tracking-stop-loss-pct", help="Attach a fixed stop-loss alert percentage to tracked buy positions."),
    tracking_stop_loss_ma_window: Optional[int] = typer.Option(None, "--tracking-stop-loss-ma-window", help="Attach a moving-average stop-loss alert window to tracked buy positions."),
    tracking_stop_loss_ticks: int = typer.Option(0, "--tracking-stop-loss-ticks", help="Attach a tick offset below the moving average for tracked buy stop-loss alerts."),
):
    """
    Scan all China A-share stocks for specific technical patterns and fundamental filters.
    """
    from squeeze.engine.patterns import detect_squeeze, detect_houyi_shooting_sun, detect_whale_trading
    from squeeze.engine.scanner import MarketScanner
    from squeeze.report.visualizer import plot_ticker

    console.print(f"[yellow]Scanning for {pattern} pattern...[/yellow]")
    
    pattern_map = {
        "squeeze": {
            "fn": detect_squeeze,
            "filter": lambda r: r.get('is_squeezed') or r.get('fired'),
            "title": "Squeeze Scan Results",
            "sort_key": lambda x: x.get('energy_level', 0)
        },
        "houyi": {
            "fn": detect_houyi_shooting_sun,
            "filter": lambda r: r.get('is_houyi'),
            "title": "Houyi Shooting the Sun Results",
            "sort_key": lambda x: x.get('rally_pct', 0)
        },
        "whale": {
            "fn": detect_whale_trading,
            "filter": lambda r: r.get('is_whale'),
            "title": "Whale Trading Alignment Results",
            "sort_key": lambda x: x.get('weekly_momentum', 0)
        }
    }
    
    if pattern not in pattern_map:
        console.print(f"[red]Unknown pattern: {pattern}.[/red]")
        return

    config = pattern_map[pattern]
    console.print("[yellow]Discovering China market tickers...[/yellow]")
    ticker_map = fetch_tickers_with_names()
    all_tickers = sorted(list(ticker_map.keys()))
    
    if limit:
        all_tickers = all_tickers[:limit]
        console.print(f"[yellow]Limiting scan to {limit} tickers.[/yellow]")
    
    console.print(f"[green]Scanning {len(all_tickers)} tickers...[/green]")
    scanner = MarketScanner(all_tickers, ticker_names=ticker_map)
    
    has_fund_filters = any([min_mkt_cap, min_volume, min_score])
    if has_fund_filters:
        with console.status("[bold green]Fetching fundamentals...[/bold green]"):
            scanner.fetch_fundamentals()
            
    with console.status("[bold green]Downloading market data...[/bold green]"):
        scanner.fetch_data(period=period)
        
    with console.status("[bold green]Analyzing patterns...[/bold green]"):
        mkt_cap_val = min_mkt_cap * 1e9 if min_mkt_cap else None
        results = scanner.scan(config['fn'], min_mkt_cap=mkt_cap_val, min_avg_volume=min_volume, min_score=min_score)

    extra_sections = {}
    if pattern == "squeeze":
        with console.status("[bold green]Checking Houyi/Whale matches...[/bold green]"):
            houyi_results = scanner.scan(detect_houyi_shooting_sun, min_mkt_cap=mkt_cap_val, min_avg_volume=min_volume, min_score=min_score)
            whale_results = scanner.scan(detect_whale_trading, min_mkt_cap=mkt_cap_val, min_avg_volume=min_volume, min_score=min_score)
        matched = _attach_pattern_flags([r for r in results if config['filter'](r)], houyi_results, whale_results)
        extra_sections = {
            "houyi": sorted([r for r in houyi_results if r.get("is_houyi")], key=lambda x: x.get("rally_pct", 0), reverse=True),
            "whale": sorted([r for r in whale_results if r.get("is_whale")], key=lambda x: x.get("weekly_momentum", 0), reverse=True),
            "priority": sorted(
                [r for r in matched if r.get("composite_score", 0) > 0],
                key=lambda x: (x.get("composite_score", 0), x.get("momentum", 0)),
                reverse=True,
            ),
        }

    if min_price is not None:
        results = [r for r in results if r.get('Close', 0) >= min_price]
    if max_price is not None:
        results = [r for r in results if r.get('Close', 0) <= max_price]

    if pattern != "squeeze":
        matched = [r for r in results if config['filter'](r)]
    matched = sorted(matched, key=config['sort_key'], reverse=True)
    
    table = Table(title=f"{config['title']} ({len(matched)} matches)")
    table.add_column("Ticker", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Signal", style="bold")
    
    if pattern == "squeeze":
        table.add_column("Energy", style="yellow")
        table.add_column("Momentum", style="green")
        table.add_column("Score", style="blue")
        for r in matched:
            energy_stars = "★" * r.get('energy_level', 0)
            momentum_color = "green" if r.get('momentum', 0) > 0 else "red"
            val_score = f"{r.get('value_score', 0):.2f}" if 'value_score' in r else "N/A"
            table.add_row(r['ticker'], r.get('name', '未知'), r.get('Signal', '觀望'), f"{r['energy_level']} {energy_stars}", f"[{momentum_color}]{r['momentum']:.4f}[/{momentum_color}]", val_score)
    
    console.print(table)
    
    buy_signals = ["強烈買入 (爆發)", "買入 (動能增強)", "觀察 (跌勢收斂)"]
    sell_signals = ["強烈賣出 (跌破)", "賣出 (動能轉弱)"]
    today_buys = [r for r in matched if r.get('Signal') in buy_signals]
    today_sells = [r for r in matched if r.get('Signal') in sell_signals]

    tracking_buys = []
    tracking_sells = []
    try:
        tracker = PerformanceTracker(Path("recommendations.csv"))
        tracker.update_daily_performance()

        market_context = tracker._infer_market_context()
        market_context['pattern'] = pattern
        tracker.record_recommendations(
            today_buys,
            rec_type='buy',
            market_context=market_context,
            stop_loss_pct=tracking_stop_loss_pct,
            stop_loss_ma_window=tracking_stop_loss_ma_window,
            stop_loss_ticks=tracking_stop_loss_ticks,
        )
        tracker.record_recommendations(today_sells, rec_type='sell', market_context=market_context)

        tracking_buys = tracker.get_active_tracking_list(rec_type='buy')
        tracking_sells = tracker.get_active_tracking_list(rec_type='sell')
    except Exception as e:
        console.print(f"[red]Error during tracking: {str(e)}[/red]")

    chart_paths = []
    if export or plot:
        base_dir = output_dir or Path("exports")
        if export:
            console.print(f"[yellow]Exporting results...[/yellow]")
            exporter = ReportExporter()
            paths = exporter.export(
                matched,
                base_dir,
                tracking_buys=tracking_buys,
                tracking_sells=tracking_sells,
                extra_sections=extra_sections,
            )
        
        if plot:
            plot_count = min(len(matched), top)
            console.print(f"[yellow]Generating charts for top {plot_count} picks...[/yellow]")
            exporter = ReportExporter()
            now = exporter._get_china_now()
            charts_dir = base_dir / now.strftime("%Y-%m-%d") / "charts"
            charts_dir.mkdir(parents=True, exist_ok=True)
            
            for i in range(plot_count):
                ticker = matched[i]['ticker']
                try:
                    ticker_data = scanner.data[ticker].dropna(subset=['Close']) if isinstance(scanner.data.columns, pd.MultiIndex) else scanner.data.dropna(subset=['Close'])
                    display_name = matched[i].get('name', ticker_map.get(ticker, "未知"))
                    chart_path = charts_dir / f"{_safe_chart_stem(ticker, display_name)}.png"
                    plot_ticker(ticker_data, f"{ticker} {display_name}", str(chart_path))
                    chart_paths.append(chart_path)
                    console.print(f"  [green]✔[/green] Generated chart for {ticker}")
                except Exception as e:
                    console.print(f"  [red]✘[/red] Error plotting {ticker}: {str(e)}")

    if notify:
        console.print("[yellow]Sending notifications...[/yellow]")
        notifier = LineNotifier()
        msg = f"Squeeze Scan Complete: {pattern}\nBuy: {len(today_buys)} | Sell: {len(today_sells)}"
        notifier.send_summary(msg)

        email_notifier = EmailNotifier()
        exporter = ReportExporter()
        html_report = exporter.render_html_summary(buy_results=today_buys, sell_results=today_sells, tracking_buys=tracking_buys, tracking_sells=tracking_sells, extra_sections=extra_sections)
        subject = f"Squeeze CN Scan Report ({pattern}) - {pd.Timestamp.now().strftime('%Y-%m-%d')}"
        
        if email_notifier.send_email(subject, html_report, is_html=True, attachments=chart_paths):
            console.print("[green]Email sent successfully with HTML and attachments.[/green]")
        else:
            console.print("[red]Failed to send email.[/red]")

if __name__ == "__main__":
    app()
