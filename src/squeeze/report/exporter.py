import csv
import json
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from jinja2 import Environment, PackageLoader, FileSystemLoader


class ReportExporter:
    """
    Orchestrates the export of scan results into multiple formats (CSV, JSON, Markdown).
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        if templates_dir is None:
            # Use PackageLoader for robust template discovery in installed packages
            self.jinja_env = Environment(
                loader=PackageLoader("squeeze.report", "templates"),
                autoescape=True
            )
        else:
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(templates_dir)),
                autoescape=True
            )

    def _get_china_now(self) -> datetime:
        """Returns the current time in China Standard Time (UTC+8)."""
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

    def _get_app_version(self) -> str:
        pyproject_path = Path(__file__).resolve().parents[3] / "pyproject.toml"
        try:
            with open(pyproject_path, "rb") as f:
                return tomllib.load(f)["project"]["version"]
        except Exception:
            return "unknown"

    def export(self, results: List[Dict[str, Any]], output_base_dir: Path) -> Dict[str, Path]:
        """
        Exports the results to CSV, JSON, and Markdown files in a date-stamped subdirectory.
        """
        # Create date-stamped subdirectory
        now = self._get_china_now()
        date_str = now.strftime("%Y-%m-%d")
        export_dir = output_base_dir / date_str
        export_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = now.strftime("%H%M%S")
        
        # Define file paths
        csv_path = export_dir / f"scan_results_{timestamp}.csv"
        json_path = export_dir / f"scan_results_{timestamp}.json"
        md_path = export_dir / f"scan_summary_{timestamp}.md"
        
        # Execute exports
        self.to_csv(results, csv_path)
        self.to_json(results, json_path)
        self.to_markdown(results, md_path)
        
        return {
            "csv": csv_path,
            "json": json_path,
            "markdown": md_path
        }

    def to_csv(self, results: List[Dict[str, Any]], path: Path) -> None:
        """Saves results to a flat CSV file."""
        if not results:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                f.write("")
            return

        headers = list(results[0].keys())
        
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(results)

    def to_json(self, results: List[Dict[str, Any]], path: Path) -> None:
        """Saves results to JSON with metadata (timestamp, patterns)."""
        data = {
            "metadata": {
                "timestamp": self._get_china_now().isoformat(),
                "count": len(results),
            },
            "results": results
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def to_markdown(self, results: List[Dict[str, Any]], path: Path) -> None:
        """Renders the Markdown summary using Jinja2."""
        # For backward compatibility, we split the results into buy/sell sections
        buy_signals = ["強烈買入 (爆發)", "買入 (動能增強)", "觀察 (跌勢收斂)"]
        sell_signals = ["強烈賣出 (跌破)", "賣出 (動能轉弱)"]

        buy_results = [r for r in results if r.get('Signal') in buy_signals]
        sell_results = [r for r in results if r.get('Signal') in sell_signals]

        content = self.render_summary(buy_results, sell_results)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def render_summary(self, 
                       buy_results: List[Dict[str, Any]] = None, 
                       sell_results: List[Dict[str, Any]] = None,
                       tracking_buys: Optional[List[Dict[str, Any]]] = None,
                       tracking_sells: Optional[List[Dict[str, Any]]] = None) -> str:
        """Renders the summary content with Buy/Sell sections and tracking."""
        template = self.jinja_env.get_template("summary.md.j2")

        buy_results = buy_results or []
        sell_results = sell_results or []

        # Take Top 10 for display in report
        top_buys = sorted(buy_results, key=lambda x: x.get('momentum', 0), reverse=True)[:10]
        top_sells = sorted(sell_results, key=lambda x: x.get('momentum', 0), reverse=False)[:10]
        render_data = {
            "date": self._get_china_now().strftime("%Y-%m-%d %H:%M:%S") + " (CST)",
            "app_version": self._get_app_version(),
            "buy_results": [self._format_result(r) for r in top_buys],
            "buy_count": len(buy_results),
            "sell_results": [self._format_result(r) for r in top_sells],
            "sell_count": len(sell_results),
            "tracking_buys": self._summarize_tracking_positions(tracking_buys or []),
            "tracking_sells": tracking_sells or []
        }

        return template.render(**render_data)

    def render_html_summary(self, 
                            buy_results: List[Dict[str, Any]] = None, 
                            sell_results: List[Dict[str, Any]] = None,
                            tracking_buys: Optional[List[Dict[str, Any]]] = None,
                            tracking_sells: Optional[List[Dict[str, Any]]] = None) -> str:
        """Renders the HTML summary content for high-quality emails."""
        template = self.jinja_env.get_template("summary.html.j2")

        buy_results = buy_results or []
        sell_results = sell_results or []

        # Take Top 10 for display
        top_buys = sorted(buy_results, key=lambda x: x.get('momentum', 0), reverse=True)[:10]
        top_sells = sorted(sell_results, key=lambda x: x.get('momentum', 0), reverse=False)[:10]
        
        render_data = {
            "date": self._get_china_now().strftime("%Y-%m-%d %H:%M:%S") + " (CST)",
            "app_version": self._get_app_version(),
            "buy_results": [self._format_result(r) for r in top_buys],
            "buy_count": len(buy_results),
            "sell_results": [self._format_result(r) for r in top_sells],
            "sell_count": len(sell_results),
            "tracking_buys": self._summarize_tracking_positions(tracking_buys or []),
            "tracking_sells": tracking_sells or []
        }

        return template.render(**render_data)

    def _summarize_tracking_positions(self, tracking_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for row in tracking_rows:
            ticker = row.get("ticker")
            if not ticker:
                continue
            grouped.setdefault(ticker, []).append(row)

        summaries = []
        for ticker, rows in grouped.items():
            ordered_rows = sorted(
                rows,
                key=lambda item: (item.get("date") or "", item.get("last_updated") or ""),
                reverse=True,
            )
            latest = dict(ordered_rows[0])
            entry_prices = [float(item["entry_price"]) for item in ordered_rows if item.get("entry_price") is not None]
            latest["entries"] = len(ordered_rows)
            latest["avg_entry_price"] = (sum(entry_prices) / len(entry_prices)) if entry_prices else latest.get("entry_price")
            latest["latest_entry_date"] = latest.get("date")
            summaries.append(latest)

        return sorted(
            summaries,
            key=lambda item: (item.get("latest_entry_date") or "", item.get("ticker") or ""),
            reverse=True,
        )

    def _format_result(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Ensures common keys exist for the template."""
        return {
            "ticker": r.get('ticker'),
            "name": r.get('name', 'Unknown'),
            "close": f"{r.get('Close', 0):.2f}",
            "momentum": r.get('momentum') or r.get('daily_momentum') or 0,
            "energy": r.get('energy_level', 0),
            "squeeze_active": r.get('is_squeezed') or r.get('is_houyi') or r.get('is_whale'),
            "signal": r.get('Signal', '觀望')
        }
