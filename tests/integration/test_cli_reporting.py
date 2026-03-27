import pytest
from typer.testing import CliRunner
from pathlib import Path
from squeeze.cli import app
import shutil

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
