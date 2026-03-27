import pandas as pd

from squeeze.report.performance import PerformanceTracker, normalize_tracking_df


def test_record_recommendations_persists_analysis_fields(tmp_path):
    tracker = PerformanceTracker(tmp_path / "recommendations.csv")
    tracker.record_recommendations(
        [
            {
                "ticker": "600519.SS",
                "name": "Kweichow Moutai",
                "Close": 100.0,
                "Signal": "買入 (動能增強)",
                "momentum": 1.2,
                "prev_momentum": 0.7,
                "energy_level": 3,
                "is_squeezed": True,
                "fired": False,
                "value_score": 0.81,
            }
        ],
        rec_type="buy",
        market_context={"pattern": "squeeze", "market_regime": "bull_trend", "benchmark_ticker": "000300.SS"},
    )

    df = pd.read_csv(tmp_path / "recommendations.csv")
    assert df.loc[0, "pattern"] == "squeeze"
    assert df.loc[0, "market_regime"] == "bull_trend"
    assert df.loc[0, "benchmark_ticker"] == "000300.SS"
    assert df.loc[0, "momentum"] == 1.2
    assert df.loc[0, "prev_momentum"] == 0.7
    assert df.loc[0, "energy_level"] == 3
    assert bool(df.loc[0, "squeeze_on"]) is True
    assert float(df.loc[0, "value_score"]) == 0.81


def test_update_daily_performance_computes_strategy_return_for_sell(tmp_path, monkeypatch):
    csv_path = tmp_path / "recommendations.csv"
    seed = pd.DataFrame(
        [
            {
                "date": "2026-03-01",
                "ticker": "600519.SS",
                "name": "Kweichow Moutai",
                "entry_price": 100.0,
                "signal": "賣出 (動能轉弱)",
                "current_price": 100.0,
                "return_pct": 0.0,
                "strategy_return_pct": 0.0,
                "days_tracked": 0,
                "last_updated": "2026-03-01",
                "status": "tracking",
                "type": "sell",
                "pattern": "squeeze",
                "momentum": -1.0,
                "prev_momentum": -0.5,
                "energy_level": 1,
                "squeeze_on": False,
                "fired": False,
                "market_regime": "bear_trend",
                "benchmark_ticker": "000300.SS",
                "value_score": None,
            }
        ]
    )
    seed.to_csv(csv_path, index=False)

    tracker = PerformanceTracker(csv_path)
    monkeypatch.setattr(
        "squeeze.report.performance.download_market_data",
        lambda tickers, period="1d": pd.DataFrame({"Close": [90.0]}),
    )
    monkeypatch.setattr(
        tracker,
        "_get_china_now",
        lambda: pd.Timestamp("2026-03-16", tz="UTC").to_pydatetime(),
    )

    results = tracker.update_daily_performance()
    updated = pd.read_csv(csv_path)
    assert len(results) == 1
    assert round(float(updated.loc[0, "return_pct"]), 2) == -10.0
    assert round(float(updated.loc[0, "strategy_return_pct"]), 2) == 10.0
    assert updated.loc[0, "status"] == "completed"


def test_normalize_tracking_df_backfills_legacy_columns():
    legacy = pd.DataFrame(
        [
            {
                "date": "2026-03-01",
                "ticker": "600519.SS",
                "name": "Kweichow Moutai",
                "entry_price": 100.0,
                "signal": "買入 (動能增強)",
                "current_price": 105.0,
                "return_pct": 5.0,
                "days_tracked": 5,
                "last_updated": "2026-03-06",
                "status": "tracking",
            }
        ]
    )

    normalized = normalize_tracking_df(legacy)
    assert normalized.loc[0, "type"] == "buy"
    assert normalized.loc[0, "strategy_return_pct"] == 5.0
    assert normalized.loc[0, "pattern"] == "squeeze"
    assert normalized.loc[0, "market_regime"] == "unknown"
