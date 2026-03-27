from typer.testing import CliRunner
from unittest.mock import MagicMock, patch

import pandas as pd

from squeeze.cli import app

runner = CliRunner()

def test_scan_reporting_integration(tmp_path):
    """
    Test the scan command with export and plot flags.
    """
    # Create a temporary export directory
    export_dir = tmp_path / "test_exports"
    
    # Run scan with larger limit to ensure we find some matches for reporting
    result = runner.invoke(app, [
        "scan", 
        "--limit", "20", 
        "--export", 
        "--plot", 
        "--top", "2", 
        "--output-dir", str(export_dir)
    ])
    
    assert result.exit_code == 0
    assert "Exporting results" in result.stdout
    assert "Generating charts" in result.stdout
    
    # Check if the date directory was created
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    expected_base = export_dir / date_str
    
    assert expected_base.exists()
    
    # Check for exported files (glob because timestamp is in filename)
    csv_files = list(expected_base.glob("scan_results_*.csv"))
    json_files = list(expected_base.glob("scan_results_*.json"))
    md_files = list(expected_base.glob("scan_summary_*.md"))
    
    assert len(csv_files) >= 1
    assert len(json_files) >= 1
    assert len(md_files) >= 1
    
    # Check for charts directory and files
    charts_dir = expected_base / "charts"
    assert charts_dir.exists()
    
    # We requested --top 2, so there should be up to 2 PNGs
    # Note: If no matches found, there might be 0, but with limit 3 
    # and no pattern filter (defaults to squeeze) it usually finds some.
    png_files = list(charts_dir.glob("*.png"))
    assert len(png_files) <= 2

def test_scan_invalid_pattern():
    """Test handling of unknown patterns."""
    result = runner.invoke(app, ["scan", "--pattern", "invalid_xyz"])
    assert result.exit_code == 0
    assert "Unknown pattern" in result.stdout


def test_plot_normalizes_cn_ticker_and_writes_named_chart(tmp_path):
    with patch("squeeze.cli.fetch_tickers_with_names") as mock_fetch, \
         patch("squeeze.engine.scanner.MarketScanner") as mock_scanner_cls, \
         patch("squeeze.report.visualizer.plot_ticker") as mock_plot:
        mock_fetch.return_value = {"002328.SZ": "新朋股份"}

        mock_scanner = MagicMock()
        mock_scanner_cls.return_value = mock_scanner
        mock_scanner.data = pd.concat({
            "002328.SZ": pd.DataFrame({
                "Close": [10.0, 10.5],
                "Open": [9.8, 10.1],
                "High": [10.2, 10.7],
                "Low": [9.7, 10.0],
                "Volume": [1000, 1200],
            })
        }, axis=1)

        output_path = tmp_path / "002328.png"
        result = runner.invoke(app, ["plot", "--ticker", "002328", "--output", str(output_path)])

        assert result.exit_code == 0
        mock_scanner_cls.assert_called_once_with(["002328.SZ"], ticker_names={"002328.SZ": "新朋股份"})
        mock_plot.assert_called_once()
        plot_args = mock_plot.call_args[0]
        assert plot_args[1] == "002328.SZ 新朋股份"
        assert plot_args[2] == str(output_path)
        assert "Saved chart:" in result.stdout


def test_analyze_normalizes_cn_ticker_and_prints_summary():
    with patch("squeeze.cli.fetch_tickers_with_names") as mock_fetch, \
         patch("squeeze.engine.scanner.MarketScanner") as mock_scanner_cls:
        mock_fetch.return_value = {"002328.SZ": "新朋股份"}

        mock_scanner = MagicMock()
        mock_scanner_cls.return_value = mock_scanner
        mock_scanner.data = pd.DataFrame({"Close": [10.0, 10.5]})
        mock_scanner.scan.return_value = [{
            "ticker": "002328.SZ",
            "name": "新朋股份",
            "Signal": "買入 (動能增強)",
            "Close": 10.5,
            "squeeze_on": True,
            "fired": False,
            "energy_level": 2,
            "momentum": 0.1234,
            "prev_momentum": 0.1000,
            "is_squeezed": True,
            "marketCap": 12e9,
        }]

        result = runner.invoke(app, ["analyze", "--ticker", "002328", "--no-fundamentals"])

        assert result.exit_code == 0
        mock_scanner_cls.assert_called_once_with(["002328.SZ"], ticker_names={"002328.SZ": "新朋股份"})
        assert "Squeeze Analysis: 002328.SZ" in result.stdout
        assert "新朋股份" in result.stdout
        assert "買入 (動能增強)" in result.stdout
