import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
from squeeze.cli import app
from pathlib import Path

runner = CliRunner()

def test_scan_automation_triggers():
    """
    Test that 'squeeze scan' with --export, --plot, and --notify
    triggers the respective components correctly.
    """
    # Mock data discovery
    with patch("squeeze.cli.fetch_tickers_with_names") as mock_fetch:
        mock_fetch.return_value = {"600519.SS": "Kweichow Moutai"}

        # Mock scanner to return a dummy result
        with patch("squeeze.engine.scanner.MarketScanner") as mock_scanner_cls, \
             patch("squeeze.cli.PerformanceTracker") as mock_tracker_cls:

            mock_scanner = MagicMock()
            mock_scanner_cls.return_value = mock_scanner

            # Mock tracker to return empty list initially
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.get_active_tracking_list.return_value = []

            # Setup scanner to return one match for squeeze
            mock_scanner.scan.return_value = [
                {
                    "ticker": "600519.SS",
                    "is_squeezed": True,
                    "energy_level": 3,
                    "momentum": 0.5,
                    "fired": False,
                    "Signal": "買入 (動能增強)"
                }
            ]            
            # Mock exporters and notifiers
            with patch("squeeze.cli.ReportExporter") as mock_exporter_cls, \
                 patch("squeeze.report.visualizer.plot_ticker") as mock_plot, \
                 patch("squeeze.cli.LineNotifier") as mock_notifier_cls, \
                 patch("squeeze.cli.EmailNotifier") as mock_email_cls:

                mock_exporter = MagicMock()
                mock_exporter_cls.return_value = mock_exporter
                mock_exporter.export.return_value = {"csv": "path/to/csv"}
                mock_exporter.render_summary.return_value = "# Chinese Summary"

                mock_notifier = MagicMock()
                mock_notifier_cls.return_value = mock_notifier
                mock_notifier.send_summary.return_value = True

                mock_email = MagicMock()
                mock_email_cls.return_value = mock_email
                mock_email.send_email.return_value = True

                # Run the command
                result = runner.invoke(app, [
                    "scan", 
                    "--limit", "1", 
                    "--export", 
                    "--plot", 
                    "--notify"
                ])

                # Check output
                assert result.exit_code == 0
                assert "Scanning for squeeze pattern" in result.stdout
                assert "600519.SS" in result.stdout
                assert "Exporting results" in result.stdout
                assert "Generating charts" in result.stdout
                assert "Sending notifications" in result.stdout
                assert "Email sent successfully with HTML and attachments." in result.stdout

                # Verify calls
                mock_exporter.export.assert_called_once()
                mock_plot.assert_called_once()
                mock_notifier.send_summary.assert_called_once()
                mock_email.send_email.assert_called_once()
                
                # Verify summary content
                args, _ = mock_notifier.send_summary.call_args
                summary_msg = args[0]
                assert "Squeeze Scan Complete" in summary_msg
                assert "Buy: 1 | Sell: 0" in summary_msg
def test_scan_houyi_triggers():
    """
    Test that 'squeeze scan --pattern houyi' correctly triggers logic.
    """
    with patch("squeeze.cli.fetch_tickers_with_names") as mock_fetch:
        mock_fetch.return_value = {"600519.SS": "Kweichow Moutai"}
        
        with patch("squeeze.engine.scanner.MarketScanner") as mock_scanner_cls, \
             patch("squeeze.cli.PerformanceTracker") as mock_tracker_cls:
            
            mock_scanner = MagicMock()
            mock_scanner_cls.return_value = mock_scanner
            mock_scanner.scan.return_value = [
                {
                    "ticker": "600519.SS",
                    "is_houyi": True,
                    "rally_pct": 0.2,
                    "fib_level": 0.5,
                    "squeeze_on": True,
                    "shooting_star": False,
                    "Signal": "買入 (動能增強)"
                }
            ]
            
            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.get_active_tracking_list.return_value = []
            
            with patch("squeeze.cli.LineNotifier") as mock_notifier_cls, \
                 patch("squeeze.cli.EmailNotifier") as mock_email_cls:
                mock_notifier = MagicMock()
                mock_notifier_cls.return_value = mock_notifier
                mock_notifier.send_summary.return_value = True
                mock_email_cls.return_value.send_email.return_value = True
                
                result = runner.invoke(app, [
                    "scan", 
                    "--pattern", "houyi",
                    "--notify"
                ])
                
                assert result.exit_code == 0
                assert "Scanning for houyi pattern" in result.stdout
                assert "Sending notifications" in result.stdout
                
                # Verify summary content
                args, _ = mock_notifier.send_summary.call_args
                summary_msg = args[0]
                assert "Squeeze Scan Complete: houyi" in summary_msg
                assert "Buy: 1 | Sell: 0" in summary_msg

def test_scan_chart_filename_includes_chinese_name():
    with patch("squeeze.cli.fetch_tickers_with_names") as mock_fetch:
        mock_fetch.return_value = {"600519.SS": "贵州茅台"}

        with patch("squeeze.engine.scanner.MarketScanner") as mock_scanner_cls, \
             patch("squeeze.cli.PerformanceTracker") as mock_tracker_cls:

            mock_scanner = MagicMock()
            mock_scanner_cls.return_value = mock_scanner
            mock_scanner.data = MagicMock()
            mock_scanner.data.columns = MagicMock()
            mock_scanner.data.columns.get_level_values.return_value = ["600519.SS"]
            mock_scanner.scan.return_value = [
                {
                    "ticker": "600519.SS",
                    "name": "贵州茅台",
                    "is_squeezed": True,
                    "energy_level": 3,
                    "momentum": 0.5,
                    "fired": False,
                    "Signal": "買入 (動能增強)"
                }
            ]

            mock_tracker = MagicMock()
            mock_tracker_cls.return_value = mock_tracker
            mock_tracker.get_active_tracking_list.return_value = []

            with patch("squeeze.cli.ReportExporter") as mock_exporter_cls, \
                 patch("squeeze.report.visualizer.plot_ticker") as mock_plot, \
                 patch("squeeze.cli.LineNotifier") as mock_notifier_cls, \
                 patch("squeeze.cli.EmailNotifier") as mock_email_cls:

                mock_exporter = MagicMock()
                mock_exporter_cls.return_value = mock_exporter
                mock_exporter.export.return_value = {"csv": "path/to/csv"}
                mock_notifier_cls.return_value.send_summary.return_value = True
                mock_email_cls.return_value.send_email.return_value = True

                result = runner.invoke(app, [
                    "scan",
                    "--limit", "1",
                    "--plot",
                    "--notify"
                ])

                assert result.exit_code == 0
                mock_plot.assert_called_once()
                plot_args = mock_plot.call_args[0]
                assert plot_args[1] == "600519.SS 贵州茅台"
                assert "600519_贵州茅台.png" in str(plot_args[2])
