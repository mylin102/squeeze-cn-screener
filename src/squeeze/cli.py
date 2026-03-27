import typer
import pandas as pd
from rich.console import Console
from rich.table import Table
from pathlib import Path

from typing import Optional

from squeeze.data.tickers import fetch_tickers_with_names
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


@app.command(name="analyze-tracking")
def analyze_tracking(
    csv_path: Path = typer.Option(Path("recommendations.csv"), "--csv", help="Tracking CSV to analyze."),
):
    """Analyze completed tracking history and summarize strategy health."""
    report = build_tracking_report(load_tracking_frame(str(csv_path)))
    console.print(format_tracking_report(report))

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
    max_price: Optional[float] = typer.Option(None, "--max-price", help="Maximum stock price (CNY)")
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
        tracker.record_recommendations(today_buys, rec_type='buy', market_context=market_context)
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
