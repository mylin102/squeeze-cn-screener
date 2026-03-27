from __future__ import annotations

from typing import Dict, Any, List

import pandas as pd

from squeeze.report.performance import normalize_tracking_df


def load_tracking_frame(csv_path: str) -> pd.DataFrame:
    return normalize_tracking_df(pd.read_csv(csv_path))


def build_tracking_report(df: pd.DataFrame) -> Dict[str, Any]:
    frame = normalize_tracking_df(df)
    if frame.empty:
        return {
            "summary": {"total_records": 0, "completed_records": 0, "active_records": 0},
            "by_type": [],
            "by_signal": [],
            "by_holding_day": [],
            "by_regime": [],
            "recommendations": ["No tracking data available."],
        }

    completed = frame[frame["status"] == "completed"].copy()
    active = frame[frame["status"] == "tracking"].copy()
    report: Dict[str, Any] = {
        "summary": {
            "total_records": int(len(frame)),
            "completed_records": int(len(completed)),
            "active_records": int(len(active)),
            "date_range": {"start": str(frame["date"].min()), "end": str(frame["date"].max())},
        }
    }

    if completed.empty:
        report.update({
            "by_type": [],
            "by_signal": [],
            "by_holding_day": [],
            "by_regime": [],
            "recommendations": [
                "No completed records yet. Let the tracker age past 14 days before changing strategy parameters.",
            ],
        })
        return report

    completed["win"] = completed["strategy_return_pct"] > 0
    completed["holding_bucket"] = completed["days_tracked"].apply(_holding_bucket)

    report["by_type"] = _aggregate(completed, ["type"], rename={"type": "bucket"})
    report["by_signal"] = _aggregate(completed, ["type", "signal"], rename={"type": "direction", "signal": "bucket"})
    report["by_holding_day"] = _aggregate(completed, ["days_tracked"], rename={"days_tracked": "bucket"})
    report["by_regime"] = _aggregate(completed, ["market_regime", "type"], rename={"market_regime": "bucket", "type": "direction"})
    report["by_holding_bucket"] = _aggregate(completed, ["holding_bucket", "type"], rename={"holding_bucket": "bucket", "type": "direction"})
    report["recommendations"] = _derive_recommendations(report)
    return report


def format_tracking_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines: List[str] = [
        "Squeeze Tracking Analysis",
        f"- Total records: {summary['total_records']}",
        f"- Completed records: {summary['completed_records']}",
        f"- Active records: {summary['active_records']}",
    ]
    date_range = summary.get("date_range")
    if date_range:
        lines.append(f"- Date range: {date_range['start']} to {date_range['end']}")

    lines.extend(_format_section("By Type", report.get("by_type", []), ["bucket"]))
    lines.extend(_format_section("By Signal", report.get("by_signal", []), ["direction", "bucket"]))
    lines.extend(_format_section("By Holding Day", report.get("by_holding_day", []), ["bucket"]))
    lines.extend(_format_section("By Regime", report.get("by_regime", []), ["bucket", "direction"]))
    lines.extend(_format_section("By Holding Bucket", report.get("by_holding_bucket", []), ["bucket", "direction"]))

    recommendations = report.get("recommendations", [])
    if recommendations:
        lines.append("")
        lines.append("Recommendations")
        for item in recommendations:
            lines.append(f"- {item}")
    return "\n".join(lines)


def _aggregate(df: pd.DataFrame, group_cols: List[str], rename: Dict[str, str]) -> List[Dict[str, Any]]:
    grouped = (
        df.groupby(group_cols, dropna=False)
        .agg(
            sample_size=("ticker", "count"),
            win_rate=("win", "mean"),
            avg_strategy_return=("strategy_return_pct", "mean"),
            median_strategy_return=("strategy_return_pct", "median"),
            avg_raw_return=("return_pct", "mean"),
        )
        .reset_index()
    )
    grouped["win_rate"] = grouped["win_rate"] * 100.0
    grouped = grouped.sort_values(by=["avg_strategy_return", "win_rate"], ascending=False)
    grouped = grouped.rename(columns=rename)
    return grouped.to_dict("records")


def _holding_bucket(days_tracked: int) -> str:
    if days_tracked <= 3:
        return "1-3d"
    if days_tracked <= 5:
        return "4-5d"
    if days_tracked <= 10:
        return "6-10d"
    return "11-14d"


def _derive_recommendations(report: Dict[str, Any]) -> List[str]:
    recommendations: List[str] = []
    by_type = {row["bucket"]: row for row in report.get("by_type", [])}
    buy_row = by_type.get("buy")
    sell_row = by_type.get("sell")
    if buy_row and buy_row["avg_strategy_return"] < 0:
        recommendations.append("Buy signals have negative average strategy return. Tighten entry filters or reduce exposure during weak market regimes.")
    if sell_row and sell_row["avg_strategy_return"] < 0:
        recommendations.append("Sell signals are not benefiting from downside follow-through. Recheck bearish signal definitions and short-side ranking.")

    holding_rows = report.get("by_holding_bucket", [])
    if holding_rows:
        best_bucket = max(holding_rows, key=lambda row: row["avg_strategy_return"])
        worst_bucket = min(holding_rows, key=lambda row: row["avg_strategy_return"])
        recommendations.append(
            f"Best holding window is {best_bucket['bucket']} ({best_bucket['avg_strategy_return']:.2f}%). Worst window is {worst_bucket['bucket']} ({worst_bucket['avg_strategy_return']:.2f}%). Use this to revisit exit timing."
        )

    signal_rows = report.get("by_signal", [])
    if signal_rows:
        weak_signals = [row for row in signal_rows if row["sample_size"] >= 3 and row["avg_strategy_return"] < 0]
        if weak_signals:
            names = ", ".join(f"{row['direction']}:{row['bucket']}" for row in weak_signals[:3])
            recommendations.append(f"Signals with repeat underperformance: {names}. Review the indicator thresholds behind these buckets.")

    if not recommendations:
        recommendations.append("No obvious failure cluster detected. Keep collecting history and validate by regime before changing core squeeze parameters.")
    return recommendations


def _format_section(title: str, rows: List[Dict[str, Any]], keys: List[str]) -> List[str]:
    if not rows:
        return []
    lines = ["", title]
    for row in rows:
        labels = " | ".join(f"{key}={row[key]}" for key in keys if key in row)
        lines.append(f"- {labels} | n={row['sample_size']} | win={row['win_rate']:.1f}% | avg={row['avg_strategy_return']:.2f}% | median={row['median_strategy_return']:.2f}%")
    return lines
