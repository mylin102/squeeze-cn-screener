import json
import csv
from pathlib import Path
import pytest
from squeeze.report.exporter import ReportExporter

@pytest.fixture
def mock_results():
    return [
        {
            "ticker": "AAPL",
            "close": 150.0,
            "momentum": 0.05,
            "energy": 0.8,
            "squeeze_active": True
        },
        {
            "ticker": "MSFT",
            "close": 300.0,
            "momentum": -0.02,
            "energy": 0.4,
            "squeeze_active": False
        },
        {
            "ticker": "GOOGL",
            "close": 2800.0,
            "momentum": 0.01,
            "energy": 0.6,
            "squeeze_active": False
        }
    ]

@pytest.fixture
def exporter():
    return ReportExporter()

def test_export_creates_directory_structure(exporter, mock_results, tmp_path):
    output_dir = tmp_path / "exports"
    paths = exporter.export(
        mock_results,
        output_dir,
        tracking_buys=[
            {
                "date": "2026-03-27",
                "ticker": "600519.SS",
                "name": "贵州茅台",
                "entry_price": 1000.0,
                "current_price": 1100.0,
                "return_pct": 10.0,
                "days_tracked": 2,
                "last_updated": "2026-03-27",
            }
        ],
    )
    
    # Check if the date directory was created
    from datetime import datetime, timedelta, timezone
    now_tst = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))
    date_str = now_tst.strftime("%Y-%m-%d")
    expected_dir = output_dir / date_str
    
    assert expected_dir.exists()
    assert expected_dir.is_dir()
    
    # Check if files exist
    assert paths["csv"].exists()
    assert paths["json"].exists()
    assert paths["markdown"].exists()
    assert "買入標的績效追蹤" in paths["markdown"].read_text(encoding="utf-8")

def test_to_csv(exporter, mock_results, tmp_path):
    csv_path = tmp_path / "test.csv"
    exporter.to_csv(mock_results, csv_path)
    
    assert csv_path.exists()
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
        assert len(rows) == 3
        assert rows[0]["ticker"] == "AAPL"
        assert float(rows[0]["close"]) == 150.0
        assert rows[0]["squeeze_active"] == "True"

def test_to_json(exporter, mock_results, tmp_path):
    json_path = tmp_path / "test.json"
    exporter.to_json(mock_results, json_path)
    
    assert json_path.exists()
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
        assert "metadata" in data
        assert data["metadata"]["count"] == 3
        assert len(data["results"]) == 3
        assert data["results"][0]["ticker"] == "AAPL"

def test_to_markdown(exporter, mock_results, tmp_path):
    # Add Signal to mock results to match new logic
    for r in mock_results:
        r['Signal'] = "買入 (動能增強)"
        r['is_squeezed'] = True
        
    md_path = tmp_path / "test.md"
    # Call render_summary with split results
    content = exporter.render_summary(buy_results=mock_results, sell_results=[])
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    assert md_path.exists()
    
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        assert "# Squeeze 技術指標掃描 - 每日摘要" in content
        assert "## 🚀 買入建議標的 (Top 10)" in content
        assert "AAPL" in content
        assert "買入 (動能增強)" in content

def test_export_empty_results(exporter, tmp_path):
    csv_path = tmp_path / "empty.csv"
    exporter.to_csv([], csv_path)
    
    assert csv_path.exists()
    with open(csv_path, 'r', encoding='utf-8') as f:
        assert f.read() == ""

def test_render_html_summary_groups_tracking_buys_by_ticker(exporter):
    html = exporter.render_html_summary(
        tracking_buys=[
            {
                "date": "2026-03-27",
                "ticker": "600519.SS",
                "name": "贵州茅台",
                "entry_price": 1000.0,
                "current_price": 1100.0,
                "return_pct": 10.0,
                "days_tracked": 2,
                "last_updated": "2026-03-27",
            },
            {
                "date": "2026-03-25",
                "ticker": "600519.SS",
                "name": "贵州茅台",
                "entry_price": 900.0,
                "current_price": 1100.0,
                "return_pct": 22.22,
                "days_tracked": 4,
                "last_updated": "2026-03-27",
            },
            {
                "date": "2026-03-26",
                "ticker": "000001.SZ",
                "name": "平安银行",
                "entry_price": 200.0,
                "current_price": 210.0,
                "return_pct": 5.0,
                "days_tracked": 3,
                "last_updated": "2026-03-27",
            },
        ]
    )

    assert html.count("<strong>600519.SS</strong>") == 1
    assert "2026-03-27" in html
    assert ">2<" in html
    assert "950.00" in html
    assert "<strong>000001.SZ</strong>" in html

def test_render_summary_groups_tracking_buys_by_ticker(exporter):
    content = exporter.render_summary(
        tracking_buys=[
            {
                "date": "2026-03-27",
                "ticker": "600519.SS",
                "name": "贵州茅台",
                "entry_price": 1000.0,
                "current_price": 1100.0,
                "return_pct": 10.0,
                "days_tracked": 2,
                "last_updated": "2026-03-27",
            },
            {
                "date": "2026-03-25",
                "ticker": "600519.SS",
                "name": "贵州茅台",
                "entry_price": 900.0,
                "current_price": 1100.0,
                "return_pct": 22.22,
                "days_tracked": 4,
                "last_updated": "2026-03-27",
            },
        ]
    )

    assert content.count("**600519.SS**") == 1
    assert "平均成本" in content
    assert "| 2026-03-27 | 2 | **600519.SS** | 贵州茅台 | 950.00 | 1100.00 | 2 | **10.00%** |" in content
