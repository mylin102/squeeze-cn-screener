import pandas as pd

from squeeze.report.tracking_analysis import build_tracking_report, format_tracking_report


def test_build_tracking_report_uses_strategy_returns():
    df = pd.DataFrame(
        [
            {
                "date": "2026-03-01",
                "ticker": "600519.SS",
                "name": "Kweichow Moutai",
                "entry_price": 100.0,
                "signal": "買入 (動能增強)",
                "current_price": 110.0,
                "return_pct": 10.0,
                "strategy_return_pct": 10.0,
                "days_tracked": 14,
                "last_updated": "2026-03-15",
                "status": "completed",
                "type": "buy",
                "pattern": "squeeze",
                "momentum": 1.1,
                "prev_momentum": 0.7,
                "energy_level": 3,
                "squeeze_on": True,
                "fired": True,
                "market_regime": "bull_trend",
                "benchmark_ticker": "000300.SS",
                "value_score": 0.9,
            },
            {
                "date": "2026-03-01",
                "ticker": "000001.SZ",
                "name": "Ping An Bank",
                "entry_price": 100.0,
                "signal": "賣出 (動能轉弱)",
                "current_price": 90.0,
                "return_pct": -10.0,
                "strategy_return_pct": 10.0,
                "days_tracked": 14,
                "last_updated": "2026-03-15",
                "status": "completed",
                "type": "sell",
                "pattern": "squeeze",
                "momentum": -1.1,
                "prev_momentum": -0.7,
                "energy_level": 1,
                "squeeze_on": False,
                "fired": False,
                "market_regime": "bear_trend",
                "benchmark_ticker": "000300.SS",
                "value_score": 0.4,
            },
        ]
    )

    report = build_tracking_report(df)
    assert report["summary"]["completed_records"] == 2
    assert report["by_type"][0]["avg_strategy_return"] == 10.0
    output = format_tracking_report(report)
    assert "By Type" in output
    assert "Recommendations" in output
