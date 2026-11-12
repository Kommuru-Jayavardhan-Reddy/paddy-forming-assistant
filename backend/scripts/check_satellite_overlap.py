"""
Check overlap between raw timeseries and regularized timeseries.
"""

import sys
import csv
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
from app import config

raw_csv = config.BASE_PROJECT_DIR / "AI_model" / "step_5_to_10" / "Step 5" / "text_and_csv_files_5" / "sentinel2_timeseries_raw.csv"
reg_csv = config.SENTINEL2_TIMESERIES_CSV_PATH

raw_data = {}
with open(raw_csv, mode="r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        key = (row["field_id"], row["date"])
        raw_data[key] = row

matches = 0
interpolated = 0
with open(reg_csv, mode="r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        key = (row["field_id"], row["date"])
        if key in raw_data:
            matches += 1
        else:
            interpolated += 1

print(f"Total regularized records: {matches + interpolated}")
print(f"Exact date matches in raw acquisitions: {matches}")
print(f"Interpolated date points: {interpolated}")
