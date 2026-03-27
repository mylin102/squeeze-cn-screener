#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from squeeze.report.tracking_analysis import build_tracking_report, format_tracking_report, load_tracking_frame


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze squeeze tracking performance.")
    parser.add_argument("--csv", default="recommendations.csv", help="Path to the tracking CSV file.")
    args = parser.parse_args()
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise SystemExit(f"Tracking file not found: {csv_path}")
    df = load_tracking_frame(str(csv_path))
    report = build_tracking_report(df)
    print(format_tracking_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
