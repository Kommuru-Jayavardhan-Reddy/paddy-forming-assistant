"""
Paddy Farming Assistant - Source Discovery & Seeding Source Inspection (STEP 11F.7)
Inspects existing project files for field metadata, GPS coordinates,
satellite observations, observation dates, and sequences.
"""

import sys
import csv
from pathlib import Path
import numpy as np

# Adjust path to import backend app config
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app import config

print("=" * 70)
print("STEP 11F.7 — PHASE A: SOURCE DISCOVERY AND INSPECTION")
print("=" * 70)

print(f"Base Project Dir: {config.BASE_PROJECT_DIR}")
print(f"Backend Dir:      {config.BACKEND_DIR}")

# 1. Inspect Master Field Mapping CSV
master_csv = config.FIELD_MASTER_MAPPING_PATH
print(f"\n1. Checking FIELD_MASTER_MAPPING_PATH: {master_csv}")
if master_csv.exists():
    print(f"   [EXISTS] File size: {master_csv.stat().st_size} bytes")
    with open(master_csv, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        fields_master = list(reader)
        print(f"   Row count: {len(fields_master)}")
        if fields_master:
            print(f"   Headers: {reader.fieldnames}")
            print(f"   Sample row 0: {fields_master[0]}")
            print(f"   Sample row last: {fields_master[-1]}")
else:
    print("   [NOT FOUND]")
    fields_master = []

# 2. Inspect Field Locations CSV
locations_csv = config.FIELD_LOCATIONS_PATH
print(f"\n2. Checking FIELD_LOCATIONS_PATH: {locations_csv}")
if locations_csv.exists():
    print(f"   [EXISTS] File size: {locations_csv.stat().st_size} bytes")
    with open(locations_csv, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        field_locs = list(reader)
        print(f"   Row count: {len(field_locs)}")
        if field_locs:
            print(f"   Headers: {reader.fieldnames}")
            print(f"   Sample row 0: {field_locs[0]}")
else:
    print("   [NOT FOUND]")
    field_locs = []

# 3. Inspect Sentinel-2 Timeseries CSV
timeseries_csv = config.SENTINEL2_TIMESERIES_CSV_PATH
print(f"\n3. Checking SENTINEL2_TIMESERIES_CSV_PATH: {timeseries_csv}")
if timeseries_csv.exists():
    print(f"   [EXISTS] File size: {timeseries_csv.stat().st_size} bytes")
    with open(timeseries_csv, mode="r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        ts_rows = list(reader)
        print(f"   Row count: {len(ts_rows)}")
        if ts_rows:
            print(f"   Headers: {reader.fieldnames}")
            print(f"   Sample row 0: {ts_rows[0]}")
            print(f"   Sample row 1: {ts_rows[1] if len(ts_rows) > 1 else 'N/A'}")
            
            # Check unique fields and counts per field
            counts_per_field = {}
            for r in ts_rows:
                fid = r.get("field_id", "")
                counts_per_field[fid] = counts_per_field.get(fid, 0) + 1
            print(f"   Unique field_ids in timeseries: {len(counts_per_field)}")
            sample_keys = list(counts_per_field.keys())[:5]
            for k in sample_keys:
                print(f"     Field '{k}': {counts_per_field[k]} observations")
else:
    print("   [NOT FOUND]")
    ts_rows = []

# 4. Inspect Satellite Sequences Tensor
seq_npy = config.SATELLITE_SEQUENCES_PATH
print(f"\n4. Checking SATELLITE_SEQUENCES_PATH: {seq_npy}")
if seq_npy.exists():
    print(f"   [EXISTS] File size: {seq_npy.stat().st_size} bytes")
    seq_arr = np.load(seq_npy, allow_pickle=False)
    print(f"   Numpy array shape: {seq_arr.shape}")
    print(f"   Dtype: {seq_arr.dtype}")
    print(f"   Min: {seq_arr.min()}, Max: {seq_arr.max()}, Has NaN: {np.isnan(seq_arr).any()}")
    print(f"   Field 0, Timestep 0: {seq_arr[0, 0]}")
    print(f"   Field 0, Timestep 9: {seq_arr[0, 9]}")
else:
    print("   [NOT FOUND]")
    seq_arr = None

# 5. Check other satellite / field files in AI_model directory
print("\n5. Searching for any other relevant CSV / JSON files in AI_model/step_5_to_10:")
step5_dir = config.BASE_PROJECT_DIR / "AI_model" / "step_5_to_10"
if step5_dir.exists():
    for p in step5_dir.rglob("*.csv"):
        print(f"   Found CSV: {p.relative_to(config.BASE_PROJECT_DIR)} ({p.stat().st_size} bytes)")
    for p in step5_dir.rglob("*.json"):
        print(f"   Found JSON: {p.relative_to(config.BASE_PROJECT_DIR)} ({p.stat().st_size} bytes)")

print("\n" + "=" * 70)
