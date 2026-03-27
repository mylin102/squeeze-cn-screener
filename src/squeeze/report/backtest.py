from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from squeeze.engine.indicators import calculate_squeeze_indicators

BUY_SIGNALS = {"強烈買入 (爆發)", "買入 (動能增強)", "觀察 (跌勢收斂)"}
SELL_SIGNALS = {"強烈賣出 (跌破)", "賣出 (動能轉弱)"}


def signal_score(signal: str) -> int:
    if signal == "強烈買入 (爆發)":
        return 3
    if signal == "買入 (動能增強)":
        return 2
    if signal == "觀察 (跌勢收斂)":
        return 1
    return 0


@dataclass
class Position:
    ticker: str
    name: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    signal: str
    momentum: float
    entry_notional: float
    entry_cost: float


def run_signal_backtest(
    price_data: pd.DataFrame,
    ticker_names: Optional[Dict[str, str]] = None,
    start_date: str = "2026-01-01",
    end_date: Optional[str] = None,
    initial_capital: float = 1_000_000.0,
    max_positions: int = 10,
    stop_loss_ma_window: Optional[int] = None,
    stop_loss_ticks: int = 0,
    tick_size: float = 0.01,
    buy_signals: Optional[set[str]] = None,
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
) -> Dict[str, Any]:
    if price_data.empty:
        raise ValueError("Price data is empty.")
    if max_positions <= 0:
        raise ValueError("max_positions must be positive.")
    if initial_capital <= 0:
        raise ValueError("initial_capital must be positive.")
    if stop_loss_ma_window is not None and stop_loss_ma_window <= 0:
        raise ValueError("stop_loss_ma_window must be positive when provided.")
    if stop_loss_ticks < 0:
        raise ValueError("stop_loss_ticks must be non-negative.")
    if tick_size <= 0:
        raise ValueError("tick_size must be positive.")
    if transaction_cost_bps < 0 or slippage_bps < 0:
        raise ValueError("transaction_cost_bps and slippage_bps must be non-negative.")

    ticker_names = ticker_names or {}
    buy_signals = buy_signals or set(BUY_SIGNALS)
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) if end_date else None
    frames = _prepare_indicator_frames(price_data, ticker_names)
    if not frames:
        raise ValueError("No valid ticker data available for backtest.")
    if stop_loss_ma_window:
        for frame in frames.values():
            frame[f"MA{stop_loss_ma_window}"] = frame["Close"].rolling(stop_loss_ma_window).mean()

    calendar = _build_calendar(frames, start_ts, end_ts)
    if not calendar:
        raise ValueError("No trading sessions found in the requested date range.")

    cash = float(initial_capital)
    positions: Dict[str, Position] = {}
    pending_buys: Dict[str, Dict[str, Any]] = {}
    pending_sells: Dict[str, Dict[str, Any]] = {}
    trades: list[Dict[str, Any]] = []
    daily_rows: list[Dict[str, Any]] = []
    previous_equity = float(initial_capital)

    for date in calendar:
        carry_buys: Dict[str, Dict[str, Any]] = {}
        carry_sells: Dict[str, Dict[str, Any]] = {}

        for ticker, order in pending_sells.items():
            frame = frames[ticker]
            row = _row_for_date(frame, date)
            if row is None:
                carry_sells[ticker] = order
                continue

            position = positions.pop(ticker, None)
            if position is None:
                continue

            raw_exit_price = float(row["Open"])
            exit_price = raw_exit_price * (1.0 - slippage_bps / 10000.0)
            gross_proceeds = position.shares * exit_price
            exit_cost = gross_proceeds * (transaction_cost_bps / 10000.0)
            net_proceeds = gross_proceeds - exit_cost
            cash += net_proceeds
            pnl = net_proceeds - position.entry_notional
            return_pct = ((net_proceeds / position.entry_notional) - 1.0) * 100.0
            holding_days = int((date - position.entry_date).days)
            trades.append(
                {
                    "ticker": ticker,
                    "name": position.name,
                    "entry_date": position.entry_date.strftime("%Y-%m-%d"),
                    "exit_date": date.strftime("%Y-%m-%d"),
                    "entry_price": round(position.entry_price, 4),
                    "exit_price": round(exit_price, 4),
                    "shares": round(position.shares, 6),
                    "notional": round(position.entry_notional, 2),
                    "pnl": round(pnl, 2),
                    "return_pct": round(return_pct, 2),
                    "holding_days": holding_days,
                    "entry_signal": position.signal,
                    "exit_signal": order["signal"],
                    "entry_cost": round(position.entry_cost, 2),
                    "exit_cost": round(exit_cost, 2),
                }
            )

        reference_equity = _portfolio_value(cash, positions, frames, date, field="Open")
        target_notional = reference_equity / max_positions
        available_slots = max_positions - len(positions)
        executable_buys = sorted(
            pending_buys.values(),
            key=lambda item: (signal_score(item["signal"]), item["momentum"]),
            reverse=True,
        )

        for order in executable_buys:
            ticker = order["ticker"]
            if ticker in positions:
                continue
            if available_slots <= 0:
                break

            frame = frames[ticker]
            row = _row_for_date(frame, date)
            if row is None:
                carry_buys[ticker] = order
                continue

            raw_entry_price = float(row["Open"])
            entry_price = raw_entry_price * (1.0 + slippage_bps / 10000.0)
            if entry_price <= 0:
                continue

            entry_cost_multiplier = 1.0 + (transaction_cost_bps / 10000.0)
            max_gross_notional = min(target_notional, cash / entry_cost_multiplier)
            if max_gross_notional <= 0:
                break

            shares = max_gross_notional / entry_price
            gross_notional = shares * entry_price
            entry_cost = gross_notional * (transaction_cost_bps / 10000.0)
            total_cash_used = gross_notional + entry_cost
            cash -= total_cash_used
            positions[ticker] = Position(
                ticker=ticker,
                name=order["name"],
                entry_date=date,
                entry_price=entry_price,
                shares=shares,
                signal=order["signal"],
                momentum=order["momentum"],
                entry_notional=gross_notional + entry_cost,
                entry_cost=entry_cost,
            )
            available_slots -= 1

        pending_buys = carry_buys
        pending_sells = carry_sells

        for ticker, frame in frames.items():
            row = _row_for_date(frame, date)
            if row is None:
                continue

            signal = str(row["Signal"])
            if ticker in positions:
                stop_loss_signal = _stop_loss_signal(
                    row=row,
                    ma_window=stop_loss_ma_window,
                    stop_loss_ticks=stop_loss_ticks,
                    tick_size=tick_size,
                )
                exit_signal = stop_loss_signal or (signal if signal in SELL_SIGNALS else None)
                if exit_signal:
                    pending_sells[ticker] = {
                        "ticker": ticker,
                        "signal": exit_signal,
                    }
                    pending_buys.pop(ticker, None)
            elif signal in buy_signals:
                pending_buys[ticker] = {
                    "ticker": ticker,
                    "name": ticker_names.get(ticker, "未知"),
                    "signal": signal,
                    "momentum": float(row["Momentum"]),
                }

        equity = _portfolio_value(cash, positions, frames, date, field="Close")
        daily_return = ((equity / previous_equity) - 1.0) if previous_equity else 0.0
        daily_rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "cash": round(cash, 2),
                "equity": round(equity, 2),
                "positions": len(positions),
                "daily_return_pct": round(daily_return * 100.0, 4),
            }
        )
        previous_equity = equity

    open_positions = _open_position_snapshots(positions, frames, calendar[-1])
    summary = _build_summary(
        daily_rows=daily_rows,
        trades=trades,
        open_positions=open_positions,
        initial_capital=initial_capital,
        ending_equity=previous_equity,
        start_date=calendar[0],
        end_date=calendar[-1],
    )
    by_signal = _aggregate_trades_by_signal(trades)

    return {
        "summary": summary,
        "config": {
            "stop_loss_ma_window": stop_loss_ma_window,
            "stop_loss_ticks": stop_loss_ticks,
            "tick_size": tick_size,
            "buy_signals": sorted(buy_signals),
            "transaction_cost_bps": transaction_cost_bps,
            "slippage_bps": slippage_bps,
        },
        "by_signal": by_signal,
        "open_positions": open_positions,
        "trades": trades,
        "equity_curve": daily_rows,
    }


def export_backtest_report(report: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _get_china_now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"backtest_{timestamp}.json"
    md_path = output_dir / f"backtest_{timestamp}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_backtest_report(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def export_rolling_backtest_report(report: Dict[str, Any], output_dir: Path) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _get_china_now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"backtest_rolling_{timestamp}.json"
    md_path = output_dir / f"backtest_rolling_{timestamp}.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_rolling_backtest_report(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def run_rolling_backtest(
    price_data: pd.DataFrame,
    ticker_names: Optional[Dict[str, str]] = None,
    start_date: str = "2026-01-01",
    end_date: Optional[str] = None,
    initial_capital: float = 1_000_000.0,
    max_positions: int = 10,
    stop_loss_ma_window: Optional[int] = None,
    stop_loss_ticks: int = 0,
    tick_size: float = 0.01,
    buy_signals: Optional[set[str]] = None,
    transaction_cost_bps: float = 0.0,
    slippage_bps: float = 0.0,
    rolling_window_sessions: int = 20,
    rolling_step_sessions: int = 10,
) -> Dict[str, Any]:
    if rolling_window_sessions <= 1:
        raise ValueError("rolling_window_sessions must be greater than 1.")
    if rolling_step_sessions <= 0:
        raise ValueError("rolling_step_sessions must be positive.")

    ticker_names = ticker_names or {}
    frames = _prepare_indicator_frames(price_data, ticker_names)
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date) if end_date else None
    calendar = _build_calendar(frames, start_ts, end_ts)
    if len(calendar) < rolling_window_sessions:
        raise ValueError("Not enough trading sessions for the requested rolling window.")

    windows: list[Dict[str, Any]] = []
    for start_idx in range(0, len(calendar) - rolling_window_sessions + 1, rolling_step_sessions):
        window_start = calendar[start_idx]
        window_end = calendar[start_idx + rolling_window_sessions - 1]
        result = run_signal_backtest(
            price_data=price_data,
            ticker_names=ticker_names,
            start_date=window_start.strftime("%Y-%m-%d"),
            end_date=window_end.strftime("%Y-%m-%d"),
            initial_capital=initial_capital,
            max_positions=max_positions,
            stop_loss_ma_window=stop_loss_ma_window,
            stop_loss_ticks=stop_loss_ticks,
            tick_size=tick_size,
            buy_signals=buy_signals,
            transaction_cost_bps=transaction_cost_bps,
            slippage_bps=slippage_bps,
        )
        summary = result["summary"]
        windows.append(
            {
                "window_index": len(windows) + 1,
                "start_date": summary["start_date"],
                "end_date": summary["end_date"],
                "trading_days": len(result.get("equity_curve", [])),
                "ending_equity": summary["ending_equity"],
                "total_return_pct": summary["total_return_pct"],
                "annualized_return_pct": summary["annualized_return_pct"],
                "max_drawdown_pct": summary["max_drawdown_pct"],
                "sharpe_ratio": summary["sharpe_ratio"],
                "closed_trades": summary["closed_trades"],
                "win_rate_pct": summary["win_rate_pct"],
                "avg_trade_return_pct": summary["avg_trade_return_pct"],
                "profit_factor": summary["profit_factor"],
            }
        )

    window_frame = pd.DataFrame(windows)
    rolling_summary = {
        "windows": int(len(windows)),
        "window_sessions": int(rolling_window_sessions),
        "step_sessions": int(rolling_step_sessions),
        "avg_window_return_pct": round(float(window_frame["total_return_pct"].mean()), 2),
        "median_window_return_pct": round(float(window_frame["total_return_pct"].median()), 2),
        "positive_window_ratio_pct": round(float((window_frame["total_return_pct"] > 0).mean() * 100.0), 2),
        "avg_window_sharpe": round(float(window_frame["sharpe_ratio"].mean()), 2),
        "worst_window_drawdown_pct": round(float(window_frame["max_drawdown_pct"].min()), 2),
        "best_window_return_pct": round(float(window_frame["total_return_pct"].max()), 2),
        "worst_window_return_pct": round(float(window_frame["total_return_pct"].min()), 2),
    }

    best_row = window_frame.sort_values(by=["total_return_pct", "sharpe_ratio"], ascending=[False, False]).iloc[0]
    worst_row = window_frame.sort_values(by=["total_return_pct", "sharpe_ratio"], ascending=[True, True]).iloc[0]

    return {
        "config": {
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "max_positions": max_positions,
            "stop_loss_ma_window": stop_loss_ma_window,
            "stop_loss_ticks": stop_loss_ticks,
            "tick_size": tick_size,
            "buy_signals": sorted(buy_signals or BUY_SIGNALS),
            "transaction_cost_bps": transaction_cost_bps,
            "slippage_bps": slippage_bps,
            "rolling_window_sessions": rolling_window_sessions,
            "rolling_step_sessions": rolling_step_sessions,
        },
        "summary": rolling_summary,
        "best_window": best_row.to_dict(),
        "worst_window": worst_row.to_dict(),
        "windows": windows,
    }


def render_backtest_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Squeeze CN Signal Backtest Report",
        f"- Period: {summary['start_date']} to {summary['end_date']}",
        f"- Initial capital: {summary['initial_capital']:,.2f}",
        f"- Ending equity: {summary['ending_equity']:,.2f}",
        f"- Total return: {summary['total_return_pct']:.2f}%",
        f"- Annualized return: {summary['annualized_return_pct']:.2f}%",
        f"- Max drawdown: {summary['max_drawdown_pct']:.2f}%",
        f"- Sharpe ratio: {summary['sharpe_ratio']:.2f}",
        f"- Closed trades: {summary['closed_trades']}",
        f"- Win rate: {summary['win_rate_pct']:.2f}%",
        f"- Avg trade return: {summary['avg_trade_return_pct']:.2f}%",
        f"- Profit factor: {summary['profit_factor']}",
        f"- Open positions: {summary['open_positions']}",
    ]
    config = report.get("config", {})
    if config.get("stop_loss_ma_window"):
        lines.append(
            f"- Stop loss: close below {config['stop_loss_ma_window']}D MA by {config['stop_loss_ticks']} ticks"
        )
    if config.get("transaction_cost_bps") or config.get("slippage_bps"):
        lines.append(
            f"- Trading frictions: cost {config.get('transaction_cost_bps', 0):.2f} bps, slippage {config.get('slippage_bps', 0):.2f} bps per side"
        )
    buy_signals = config.get("buy_signals")
    if buy_signals:
        lines.append(f"- Buy signals: {', '.join(buy_signals)}")

    signal_rows = report.get("by_signal", [])
    if signal_rows:
        lines.extend(
            [
                "",
                "## By Entry Signal",
                "| Signal | Trades | Win Rate | Avg Return |",
                "| :--- | ---: | ---: | ---: |",
            ]
        )
        for row in signal_rows:
            lines.append(
                f"| {row['entry_signal']} | {row['trades']} | {row['win_rate_pct']:.2f}% | {row['avg_return_pct']:.2f}% |"
            )

    open_positions = report.get("open_positions", [])
    if open_positions:
        lines.extend(
            [
                "",
                "## Open Positions",
                "| Ticker | Name | Entry Date | Entry Price | Last Close | Unrealized Return |",
                "| :--- | :--- | :--- | ---: | ---: | ---: |",
            ]
        )
        for row in open_positions:
            lines.append(
                f"| {row['ticker']} | {row['name']} | {row['entry_date']} | {row['entry_price']:.2f} | {row['last_close']:.2f} | {row['unrealized_return_pct']:.2f}% |"
            )

    trade_rows = report.get("trades", [])[:20]
    if trade_rows:
        lines.extend(
            [
                "",
                "## Closed Trades Preview",
                "| Ticker | Entry Date | Exit Date | Entry Signal | Exit Signal | Return |",
                "| :--- | :--- | :--- | :--- | :--- | ---: |",
            ]
        )
        for row in trade_rows:
            lines.append(
                f"| {row['ticker']} | {row['entry_date']} | {row['exit_date']} | {row['entry_signal']} | {row['exit_signal']} | {row['return_pct']:.2f}% |"
            )

    return "\n".join(lines) + "\n"


def render_rolling_backtest_report(report: Dict[str, Any]) -> str:
    summary = report["summary"]
    config = report["config"]
    best_window = report["best_window"]
    worst_window = report["worst_window"]
    lines = [
        "# Squeeze CN Rolling Backtest Report",
        f"- Period: {config['start_date']} to {config['end_date'] or 'latest'}",
        f"- Rolling window: {summary['window_sessions']} sessions",
        f"- Step size: {summary['step_sessions']} sessions",
        f"- Windows tested: {summary['windows']}",
        f"- Avg window return: {summary['avg_window_return_pct']:.2f}%",
        f"- Median window return: {summary['median_window_return_pct']:.2f}%",
        f"- Positive window ratio: {summary['positive_window_ratio_pct']:.2f}%",
        f"- Avg window Sharpe: {summary['avg_window_sharpe']:.2f}",
        f"- Worst window drawdown: {summary['worst_window_drawdown_pct']:.2f}%",
        f"- Best window return: {summary['best_window_return_pct']:.2f}%",
        f"- Worst window return: {summary['worst_window_return_pct']:.2f}%",
    ]
    if config.get("stop_loss_ma_window"):
        lines.append(
            f"- Stop loss: close below {config['stop_loss_ma_window']}D MA by {config['stop_loss_ticks']} ticks"
        )
    if config.get("transaction_cost_bps") or config.get("slippage_bps"):
        lines.append(
            f"- Trading frictions: cost {config.get('transaction_cost_bps', 0):.2f} bps, slippage {config.get('slippage_bps', 0):.2f} bps per side"
        )
    buy_signals = config.get("buy_signals")
    if buy_signals:
        lines.append(f"- Buy signals: {', '.join(buy_signals)}")

    lines.extend(
        [
            "",
            "## Best Window",
            f"- Window #{int(best_window['window_index'])}: {best_window['start_date']} to {best_window['end_date']}",
            f"- Return: {best_window['total_return_pct']:.2f}%, Max drawdown: {best_window['max_drawdown_pct']:.2f}%, Sharpe: {best_window['sharpe_ratio']:.2f}",
            "",
            "## Worst Window",
            f"- Window #{int(worst_window['window_index'])}: {worst_window['start_date']} to {worst_window['end_date']}",
            f"- Return: {worst_window['total_return_pct']:.2f}%, Max drawdown: {worst_window['max_drawdown_pct']:.2f}%, Sharpe: {worst_window['sharpe_ratio']:.2f}",
            "",
            "## Window Results",
            "| Window | Start | End | Days | Return | Max Drawdown | Sharpe | Closed Trades | Win Rate | Ending Equity |",
            "| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report.get("windows", []):
        lines.append(
            f"| {row['window_index']} | {row['start_date']} | {row['end_date']} | {row['trading_days']} | {row['total_return_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['closed_trades']} | {row['win_rate_pct']:.2f}% | {row['ending_equity']:,.2f} |"
        )
    return "\n".join(lines) + "\n"


def render_backtest_grid_report(rows: list[Dict[str, Any]], start_date: str, end_date: str) -> str:
    lines = [
        "# Squeeze CN Stop-Loss Grid Report",
        f"- Period: {start_date} to {end_date}",
        "",
        "| MA Window | Ticks | Total Return | Max Drawdown | Sharpe | Win Rate | Avg Trade | Profit Factor | Ending Equity |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['ma_window']} | {row['ticks']} | {row['total_return_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['sharpe_ratio']:.2f} | {row['win_rate_pct']:.2f}% | {row['avg_trade_return_pct']:.2f}% | {row['profit_factor']} | {row['ending_equity']:,.2f} |"
        )
    return "\n".join(lines) + "\n"


def _prepare_indicator_frames(price_data: pd.DataFrame, ticker_names: Dict[str, str]) -> Dict[str, pd.DataFrame]:
    frames: Dict[str, pd.DataFrame] = {}
    if isinstance(price_data.columns, pd.MultiIndex):
        tickers = list(price_data.columns.get_level_values(0).unique())
        for ticker in tickers:
            ticker_df = price_data[ticker].dropna(subset=["Close"]).copy()
            if len(ticker_df) < 30:
                continue
            frames[ticker] = calculate_squeeze_indicators(ticker_df)
    else:
        if len(price_data) >= 30:
            ticker = next(iter(ticker_names.keys()), "SINGLE")
            frames[ticker] = calculate_squeeze_indicators(price_data.dropna(subset=["Close"]).copy())
    return frames


def _stop_loss_signal(
    row: pd.Series,
    ma_window: Optional[int],
    stop_loss_ticks: int,
    tick_size: float,
) -> Optional[str]:
    if not ma_window:
        return None

    ma_value = row.get(f"MA{ma_window}")
    close_price = row.get("Close")
    if pd.isna(ma_value) or pd.isna(close_price):
        return None

    threshold = float(ma_value) - (stop_loss_ticks * tick_size)
    if float(close_price) < threshold:
        return f"停損: 跌破{ma_window}日線下{stop_loss_ticks}檔"
    return None


def _build_calendar(
    frames: Dict[str, pd.DataFrame],
    start_ts: pd.Timestamp,
    end_ts: Optional[pd.Timestamp],
) -> list[pd.Timestamp]:
    dates: set[pd.Timestamp] = set()
    for frame in frames.values():
        for date in frame.index:
            if date >= start_ts and (end_ts is None or date <= end_ts):
                dates.add(pd.Timestamp(date))
    return sorted(dates)


def _row_for_date(frame: pd.DataFrame, date: pd.Timestamp) -> Optional[pd.Series]:
    if date not in frame.index:
        return None
    row = frame.loc[date]
    if isinstance(row, pd.DataFrame):
        return row.iloc[-1]
    return row


def _price_on_or_before(frame: pd.DataFrame, date: pd.Timestamp, field: str) -> Optional[float]:
    subset = frame.loc[:date]
    if subset.empty:
        return None
    return float(subset.iloc[-1][field])


def _portfolio_value(
    cash: float,
    positions: Dict[str, Position],
    frames: Dict[str, pd.DataFrame],
    date: pd.Timestamp,
    field: str,
) -> float:
    total = cash
    for ticker, position in positions.items():
        price = _price_on_or_before(frames[ticker], date, field)
        if price is None:
            price = position.entry_price
        total += position.shares * price
    return total


def _open_position_snapshots(
    positions: Dict[str, Position],
    frames: Dict[str, pd.DataFrame],
    end_date: pd.Timestamp,
) -> list[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for ticker, position in positions.items():
        last_close = _price_on_or_before(frames[ticker], end_date, "Close")
        if last_close is None:
            continue
        rows.append(
            {
                "ticker": ticker,
                "name": position.name,
                "entry_date": position.entry_date.strftime("%Y-%m-%d"),
                "entry_price": round(position.entry_price, 4),
                "last_close": round(last_close, 4),
                "unrealized_return_pct": round(((last_close / position.entry_price) - 1.0) * 100.0, 2),
            }
        )
    return sorted(rows, key=lambda item: item["unrealized_return_pct"], reverse=True)


def _build_summary(
    daily_rows: list[Dict[str, Any]],
    trades: list[Dict[str, Any]],
    open_positions: list[Dict[str, Any]],
    initial_capital: float,
    ending_equity: float,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> Dict[str, Any]:
    equity_series = pd.Series([row["equity"] for row in daily_rows], dtype=float)
    daily_returns = equity_series.pct_change().dropna()
    total_return_pct = ((ending_equity / initial_capital) - 1.0) * 100.0
    trading_days = max(len(equity_series), 1)
    annualized_return_pct = (((ending_equity / initial_capital) ** (252 / trading_days)) - 1.0) * 100.0 if trading_days > 1 else total_return_pct
    drawdown = (equity_series / equity_series.cummax()) - 1.0 if not equity_series.empty else pd.Series(dtype=float)
    max_drawdown_pct = float(drawdown.min() * 100.0) if not drawdown.empty else 0.0
    volatility = float(daily_returns.std() * (252 ** 0.5) * 100.0) if len(daily_returns) > 1 else 0.0
    sharpe_ratio = float((daily_returns.mean() / daily_returns.std()) * (252 ** 0.5)) if len(daily_returns) > 1 and daily_returns.std() > 0 else 0.0

    trade_returns = pd.Series([row["return_pct"] for row in trades], dtype=float)
    positive = trade_returns[trade_returns > 0].sum()
    negative = trade_returns[trade_returns < 0].sum()
    profit_factor: Any
    if negative < 0:
        profit_factor = round(float(positive / abs(negative)), 2)
    elif positive > 0:
        profit_factor = "inf"
    else:
        profit_factor = "n/a"

    return {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "initial_capital": round(initial_capital, 2),
        "ending_equity": round(ending_equity, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(annualized_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "annualized_volatility_pct": round(volatility, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "closed_trades": int(len(trades)),
        "open_positions": int(len(open_positions)),
        "win_rate_pct": round(float((trade_returns > 0).mean() * 100.0), 2) if not trade_returns.empty else 0.0,
        "avg_trade_return_pct": round(float(trade_returns.mean()), 2) if not trade_returns.empty else 0.0,
        "median_trade_return_pct": round(float(trade_returns.median()), 2) if not trade_returns.empty else 0.0,
        "avg_holding_days": round(float(pd.Series([row["holding_days"] for row in trades], dtype=float).mean()), 2) if trades else 0.0,
        "profit_factor": profit_factor,
    }


def _aggregate_trades_by_signal(trades: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    if not trades:
        return []
    frame = pd.DataFrame(trades)
    grouped = (
        frame.groupby("entry_signal", dropna=False)
        .agg(
            trades=("ticker", "count"),
            win_rate_pct=("return_pct", lambda s: (s > 0).mean() * 100.0),
            avg_return_pct=("return_pct", "mean"),
        )
        .reset_index()
        .sort_values(by=["avg_return_pct", "trades"], ascending=[False, False])
    )
    grouped["win_rate_pct"] = grouped["win_rate_pct"].round(2)
    grouped["avg_return_pct"] = grouped["avg_return_pct"].round(2)
    return grouped.to_dict("records")


def _get_china_now() -> datetime:
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
