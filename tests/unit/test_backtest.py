from pathlib import Path
from unittest.mock import patch

import pandas as pd

from squeeze.report.backtest import (
    export_backtest_report,
    export_rolling_backtest_report,
    render_backtest_grid_report,
    render_backtest_report,
    render_rolling_backtest_report,
    run_rolling_backtest,
    run_signal_backtest,
)


def _make_price_data() -> pd.DataFrame:
    dates = pd.bdate_range("2025-11-17", periods=40)
    ticker_df = pd.DataFrame(
        {
            "Open": [100 + i for i in range(len(dates))],
            "High": [101 + i for i in range(len(dates))],
            "Low": [99 + i for i in range(len(dates))],
            "Close": [100 + i for i in range(len(dates))],
            "Volume": [1000 + i for i in range(len(dates))],
        },
        index=dates,
    )
    return pd.concat({"600000.SS": ticker_df}, axis=1)


def _fake_indicator_frame(raw_df: pd.DataFrame) -> pd.DataFrame:
    frame = raw_df.copy()
    frame["Squeeze_On"] = False
    frame["Energy_Level"] = 0
    frame["Momentum"] = 0.0
    frame["Prev_Momentum"] = 0.0
    frame["Fired"] = False
    frame["Signal"] = "觀望 (動能減弱)"

    frame.loc[pd.Timestamp("2026-01-01"), "Signal"] = "買入 (動能增強)"
    frame.loc[pd.Timestamp("2026-01-01"), "Momentum"] = 0.8
    frame.loc[pd.Timestamp("2026-01-05"), "Signal"] = "賣出 (動能轉弱)"
    frame.loc[pd.Timestamp("2026-01-05"), "Momentum"] = -0.5
    return frame


def test_run_signal_backtest_executes_next_day_entries_and_exits():
    price_data = _make_price_data()

    with patch("squeeze.report.backtest.calculate_squeeze_indicators", side_effect=_fake_indicator_frame):
        report = run_signal_backtest(
            price_data=price_data,
            ticker_names={"600000.SS": "浦发银行"},
            start_date="2026-01-01",
            end_date="2026-01-15",
            initial_capital=100000.0,
            max_positions=2,
        )

    assert report["summary"]["closed_trades"] == 1
    assert report["summary"]["open_positions"] == 0

    trade = report["trades"][0]
    assert trade["ticker"] == "600000.SS"
    assert trade["entry_date"] == "2026-01-02"
    assert trade["exit_date"] == "2026-01-06"
    assert trade["entry_signal"] == "買入 (動能增強)"
    assert trade["exit_signal"] == "賣出 (動能轉弱)"
    assert trade["return_pct"] > 0


def test_render_and_export_backtest_report(tmp_path):
    report = {
        "summary": {
            "start_date": "2026-01-01",
            "end_date": "2026-03-28",
            "initial_capital": 1_000_000.0,
            "ending_equity": 1_080_000.0,
            "total_return_pct": 8.0,
            "annualized_return_pct": 35.0,
            "max_drawdown_pct": -4.5,
            "annualized_volatility_pct": 12.0,
            "sharpe_ratio": 1.8,
            "closed_trades": 5,
            "open_positions": 1,
            "win_rate_pct": 60.0,
            "avg_trade_return_pct": 3.2,
            "median_trade_return_pct": 2.5,
            "avg_holding_days": 4.2,
            "profit_factor": 1.9,
        },
        "config": {
            "stop_loss_ma_window": 20,
            "stop_loss_ticks": 2,
            "tick_size": 0.01,
            "buy_signals": ["強烈買入 (爆發)", "買入 (動能增強)", "觀察 (跌勢收斂)"],
            "transaction_cost_bps": 10.0,
            "slippage_bps": 5.0,
        },
        "by_signal": [
            {"entry_signal": "強烈買入 (爆發)", "trades": 2, "win_rate_pct": 100.0, "avg_return_pct": 6.5}
        ],
        "open_positions": [
            {
                "ticker": "600000.SS",
                "name": "浦发银行",
                "entry_date": "2026-03-20",
                "entry_price": 120.0,
                "last_close": 125.0,
                "unrealized_return_pct": 4.17,
            }
        ],
        "trades": [
            {
                "ticker": "600000.SS",
                "entry_date": "2026-01-02",
                "exit_date": "2026-01-06",
                "entry_signal": "買入 (動能增強)",
                "exit_signal": "賣出 (動能轉弱)",
                "return_pct": 5.1,
            }
        ],
        "equity_curve": [],
    }

    content = render_backtest_report(report)
    assert "Squeeze CN Signal Backtest Report" in content
    assert "Total return: 8.00%" in content
    assert "Open Positions" in content
    assert "Stop loss: close below 20D MA by 2 ticks" in content
    assert "Trading frictions: cost 10.00 bps, slippage 5.00 bps per side" in content

    paths = export_backtest_report(report, tmp_path / "backtests")
    assert paths["markdown"].exists()
    assert paths["json"].exists()
    assert "By Entry Signal" in paths["markdown"].read_text(encoding="utf-8")


def test_run_signal_backtest_supports_ma_stop_loss():
    price_data = _make_price_data()

    def fake_indicator(raw_df: pd.DataFrame) -> pd.DataFrame:
        frame = raw_df.copy()
        frame["Squeeze_On"] = False
        frame["Energy_Level"] = 0
        frame["Momentum"] = 0.0
        frame["Prev_Momentum"] = 0.0
        frame["Fired"] = False
        frame["Signal"] = "觀望 (動能減弱)"
        frame.loc[pd.Timestamp("2026-01-01"), "Signal"] = "買入 (動能增強)"
        frame.loc[pd.Timestamp("2026-01-01"), "Momentum"] = 0.8
        frame.loc[pd.Timestamp("2026-01-05"), "Close"] = 90.0
        return frame

    with patch("squeeze.report.backtest.calculate_squeeze_indicators", side_effect=fake_indicator):
        report = run_signal_backtest(
            price_data=price_data,
            ticker_names={"600000.SS": "浦发银行"},
            start_date="2026-01-01",
            end_date="2026-01-15",
            initial_capital=100000.0,
            max_positions=2,
            stop_loss_ma_window=20,
            stop_loss_ticks=2,
        )

    trade = report["trades"][0]
    assert trade["exit_date"] == "2026-01-06"
    assert trade["exit_signal"] == "停損: 跌破20日線下2檔"


def test_run_signal_backtest_applies_costs_and_signal_filter():
    price_data = _make_price_data()

    def fake_indicator(raw_df: pd.DataFrame) -> pd.DataFrame:
        frame = raw_df.copy()
        frame["Squeeze_On"] = False
        frame["Energy_Level"] = 0
        frame["Momentum"] = 0.0
        frame["Prev_Momentum"] = 0.0
        frame["Fired"] = False
        frame["Signal"] = "觀望 (動能減弱)"
        frame.loc[pd.Timestamp("2026-01-01"), "Signal"] = "觀察 (跌勢收斂)"
        frame.loc[pd.Timestamp("2026-01-02"), "Signal"] = "買入 (動能增強)"
        frame.loc[pd.Timestamp("2026-01-05"), "Signal"] = "賣出 (動能轉弱)"
        frame.loc[pd.Timestamp("2026-01-02"), "Momentum"] = 0.8
        return frame

    with patch("squeeze.report.backtest.calculate_squeeze_indicators", side_effect=fake_indicator):
        report = run_signal_backtest(
            price_data=price_data,
            ticker_names={"600000.SS": "浦发银行"},
            start_date="2026-01-01",
            end_date="2026-01-15",
            initial_capital=100000.0,
            max_positions=2,
            buy_signals={"買入 (動能增強)"},
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
        )

    trade = report["trades"][0]
    assert trade["entry_date"] == "2026-01-05"
    assert trade["entry_signal"] == "買入 (動能增強)"
    assert trade["entry_cost"] > 0
    assert trade["exit_cost"] > 0
    assert report["config"]["buy_signals"] == ["買入 (動能增強)"]


def test_render_backtest_grid_report():
    content = render_backtest_grid_report(
        [
            {
                "ma_window": 20,
                "ticks": 2,
                "total_return_pct": 56.26,
                "max_drawdown_pct": -8.08,
                "sharpe_ratio": 5.50,
                "win_rate_pct": 35.0,
                "avg_trade_return_pct": 4.04,
                "profit_factor": 1.8,
                "ending_equity": 1562633.04,
            }
        ],
        "2026-01-01",
        "2026-03-27",
    )
    assert "Squeeze CN Stop-Loss Grid Report" in content
    assert "| 20 | 2 | 56.26% | -8.08% | 5.50 | 35.00% | 4.04% | 1.8 | 1,562,633.04 |" in content


def test_run_rolling_backtest_and_export(tmp_path):
    price_data = _make_price_data()

    with patch("squeeze.report.backtest.calculate_squeeze_indicators", side_effect=_fake_indicator_frame):
        report = run_rolling_backtest(
            price_data=price_data,
            ticker_names={"600000.SS": "浦发银行"},
            start_date="2026-01-01",
            end_date="2026-01-23",
            initial_capital=100000.0,
            max_positions=2,
            stop_loss_ma_window=20,
            stop_loss_ticks=2,
            transaction_cost_bps=10.0,
            slippage_bps=5.0,
            rolling_window_sessions=5,
            rolling_step_sessions=2,
        )

    assert report["summary"]["windows"] >= 1
    assert report["config"]["rolling_window_sessions"] == 5
    assert report["best_window"]["start_date"] <= report["best_window"]["end_date"]

    content = render_rolling_backtest_report(report)
    assert "Squeeze CN Rolling Backtest Report" in content
    assert "Rolling window: 5 sessions" in content
    assert "Trading frictions: cost 10.00 bps, slippage 5.00 bps per side" in content

    paths = export_rolling_backtest_report(report, tmp_path / "rolling")
    assert paths["markdown"].exists()
    assert paths["json"].exists()
