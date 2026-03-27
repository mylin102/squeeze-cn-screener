#!/usr/bin/env python3
"""
Generate a historical `recommendations.csv` from a backtest report so the tracker
can analyze records dating back to the start of the simulation.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

import pandas as pd


TRACKING_COLUMNS = [
    "date",
    "ticker",
    "name",
    "entry_price",
    "signal",
    "current_price",
    "return_pct",
    "strategy_return_pct",
    "days_tracked",
    "last_updated",
    "status",
    "type",
    "pattern",
    "momentum",
    "prev_momentum",
    "energy_level",
    "squeeze_on",
    "fired",
    "market_regime",
    "benchmark_ticker",
    "value_score",
    "stop_loss_rule",
    "stop_loss_threshold",
    "stop_loss_triggered",
    "stop_loss_message",
    "stop_loss_ma_window",
    "stop_loss_ticks",
    "stop_loss_tick_size",
]


def _build_stop_loss_rule(config: Dict[str, Any]) -> str:
    parts: List[str] = []
    pct = config.get("stop_loss_pct")
    if pct:
        parts.append(f"fixed_pct_{float(pct):.2f}")
    ma = config.get("stop_loss_ma_window")
    ticks = config.get("stop_loss_ticks")
    if ma and ma > 0:
        parts.append(f"ma{ma}_ticks{ticks}")
    return " / ".join(parts) if parts else ""


def _build_trade_row(trade: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": trade["entry_date"],
        "ticker": trade["ticker"],
        "name": trade.get("name", ""),
        "entry_price": trade["entry_price"],
        "signal": trade.get("entry_signal", "unknown"),
        "current_price": trade.get("exit_price", trade["entry_price"]),
        "return_pct": trade.get("return_pct", 0.0),
        "strategy_return_pct": trade.get("return_pct", 0.0),
        "days_tracked": trade.get("holding_days", 0),
        "last_updated": trade.get("exit_date", trade["entry_date"]),
        "status": "completed",
        "type": "buy",
        "pattern": "squeeze",
        "momentum": 0.0,
        "prev_momentum": 0.0,
        "energy_level": 0,
        "squeeze_on": False,
        "fired": False,
        "market_regime": "unknown",
        "benchmark_ticker": config.get("benchmark_ticker", "000300.SS"),
        "value_score": None,
        "stop_loss_rule": _build_stop_loss_rule(config),
        "stop_loss_threshold": config.get("stop_loss_pct"),
        "stop_loss_triggered": False,
        "stop_loss_message": None,
        "stop_loss_ma_window": config.get("stop_loss_ma_window"),
        "stop_loss_ticks": config.get("stop_loss_ticks", 0),
        "stop_loss_tick_size": config.get("tick_size", 0.01),
    }


def _build_open_position_row(position: Dict[str, Any], config: Dict[str, Any], end_date: str) -> Dict[str, Any]:
    entry_date = datetime.strptime(position["entry_date"], "%Y-%m-%d")
    end_day = datetime.strptime(end_date, "%Y-%m-%d")
    return {
        "date": position["entry_date"],
        "ticker": position["ticker"],
        "name": position.get("name", ""),
        "entry_price": position["entry_price"],
        "signal": position.get("entry_signal", "unknown"),
        "current_price": position["last_close"],
        "return_pct": position.get("unrealized_return_pct", 0.0),
        "strategy_return_pct": position.get("unrealized_return_pct", 0.0),
        "days_tracked": (end_day - entry_date).days,
        "last_updated": end_date,
        "status": "tracking",
        "type": "buy",
        "pattern": "squeeze",
        "momentum": 0.0,
        "prev_momentum": 0.0,
        "energy_level": 0,
        "squeeze_on": False,
        "fired": False,
        "market_regime": "unknown",
        "benchmark_ticker": config.get("benchmark_ticker", "000300.SS"),
        "value_score": None,
        "stop_loss_rule": _build_stop_loss_rule(config),
        "stop_loss_threshold": config.get("stop_loss_pct"),
        "stop_loss_triggered": False,
        "stop_loss_message": None,
        "stop_loss_ma_window": config.get("stop_loss_ma_window"),
        "stop_loss_ticks": config.get("stop_loss_ticks", 0),
        "stop_loss_tick_size": config.get("tick_size", 0.01),
    }


def backfill(report_path: Path, output: Path) -> None:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    config = payload.get("config", {})
    end_date = payload["summary"]["end_date"]

    trades = payload.get("trades", [])
    rows = [_build_trade_row(trade, config) for trade in trades]
    rows += [
        _build_open_position_row(pos, config, end_date)
        for pos in payload.get("open_positions", [])
    ]

    for row in rows:
        for col in TRACKING_COLUMNS:
            row.setdefault(col, None)

    df = pd.DataFrame(rows, columns=TRACKING_COLUMNS)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False, encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed recommendations.csv from a backtest report")
    parser.add_argument(
        "--report",
        type=Path,
        required=True,
        help="Path to the backtest JSON report (exports/backtests/…/*.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "recommendations.csv",
        help="Destination for the generated recommendations.csv",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    backfill(args.report, args.output)
    print(f"Generated {args.output} from {args.report}")


if __name__ == "__main__":
    main()
