"""
Check uniqueness and validity of dates and values in sentinel2_timeseries.csv
and step7_verified_field_embedding_mapping.csv
"""

import sys
import csv
from datetime import datetime
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))
from app import config

print("=" * 70)
print("VALIDATING SOURCE DATA FOR SEEDING")
print("=" * 70)

# 1. Validate fields master mapping
master_csv = config.FIELD_MASTER_MAPPING_PATH
field_ids = []
clean_field_ids = []
latitudes = []
longitudes = []
field_records = []

with open(master_csv, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        fid = row["field_id"]
        cid = row.get("clean_field_id", "")
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        seq_idx = int(row.get("sequence_index", -1))
        
        field_ids.append(fid)
        clean_field_ids.append(cid)
        latitudes.append(lat)
        longitudes.append(lon)
        field_records.append({
            "external_field_id": fid,
            "clean_field_id": cid,
            "latitude": lat,
            "longitude": lon,
            "sequence_index": seq_idx,
            "sentinel2_image_count": int(row.get("sentinel2_image_count", 0)),
        })

print(f"Total fields read: {len(field_records)}")
print(f"Unique external_field_ids: {len(set(field_ids))}")
print(f"Unique clean_field_ids:    {len(set(clean_field_ids))}")

# Check GPS bounds
bad_lats = [lat for lat in latitudes if not (-90.0 <= lat <= 90.0)]
bad_lons = [lon for lon in longitudes if not (-180.0 <= lon <= 180.0)]
print(f"Invalid latitudes: {len(bad_lats)}")
print(f"Invalid longitudes: {len(bad_lons)}")
print(f"Latitude range:  [{min(latitudes):.6f}, {max(latitudes):.6f}]")
print(f"Longitude range: [{min(longitudes):.6f}, {max(longitudes):.6f}]")

# 2. Validate satellite timeseries CSV
ts_csv = config.SENTINEL2_TIMESERIES_CSV_PATH
ts_records = []
field_date_set = set()
duplicate_field_dates = []
invalid_dates = []
invalid_indices = []

with open(ts_csv, mode="r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        fid = row["field_id"]
        timestep = int(row["time_step"])
        date_str = row["date"]
        ndvi = float(row["NDVI"])
        ndre = float(row["NDRE"])
        gndvi = float(row["GNDVI"])
        
        # Check date format
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception as e:
            invalid_dates.append((i, fid, date_str, str(e)))
            continue
            
        # Check index bounds [-1.0, 1.0]
        if not (-1.0 <= ndvi <= 1.0) or not (-1.0 <= ndre <= 1.0) or not (-1.0 <= gndvi <= 1.0):
            invalid_indices.append((i, fid, ndvi, ndre, gndvi))
            
        key = (fid, date_str)
        if key in field_date_set:
            duplicate_field_dates.append(key)
        else:
            field_date_set.add(key)
            
        ts_records.append({
            "external_field_id": fid,
            "time_step": timestep,
            "observation_date": parsed_date,
            "ndvi": ndvi,
            "ndre": ndre,
            "gndvi": gndvi,
            "is_interpolated": True,
            "data_source": "Sentinel-2 L2A"
        })

print(f"\nTotal satellite observation rows read: {len(ts_records)}")
print(f"Invalid dates: {len(invalid_dates)}")
print(f"Invalid vegetation indices outside [-1, 1]: {len(invalid_indices)}")
print(f"Duplicate (field_id, date) pairs: {len(duplicate_field_dates)}")

# Check per field counts
ts_by_field = {}
for r in ts_records:
    fid = r["external_field_id"]
    ts_by_field[fid] = ts_by_field.get(fid, 0) + 1

fields_without_10 = {f: c for f, c in ts_by_field.items() if c != 10}
missing_from_ts = [f for f in field_ids if f not in ts_by_field]
print(f"Fields without exactly 10 observations: {len(fields_without_10)}")
print(f"Fields in master catalog missing from timeseries: {len(missing_from_ts)}")

print("\nSample observation 0:")
print(f"  Field: {ts_records[0]['external_field_id']}")
print(f"  Step:  {ts_records[0]['time_step']}")
print(f"  Date:  {ts_records[0]['observation_date']}")
print(f"  NDVI:  {ts_records[0]['ndvi']}, NDRE: {ts_records[0]['ndre']}, GNDVI: {ts_records[0]['gndvi']}")

print("\nSample observation 9 (FIELD_01):")
print(f"  Field: {ts_records[9]['external_field_id']}")
print(f"  Step:  {ts_records[9]['time_step']}")
print(f"  Date:  {ts_records[9]['observation_date']}")
print(f"  NDVI:  {ts_records[9]['ndvi']}, NDRE: {ts_records[9]['ndre']}, GNDVI: {ts_records[9]['gndvi']}")

print("\n" + "=" * 70)
