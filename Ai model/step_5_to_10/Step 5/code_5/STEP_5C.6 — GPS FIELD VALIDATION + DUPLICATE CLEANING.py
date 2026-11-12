
# ============================================================
# STEP_5C.6 — GPS FIELD VALIDATION + DUPLICATE CLEANING
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.cluster import DBSCAN

from google.colab import drive

# ============================================================
# 1. MOUNT GOOGLE DRIVE
# ============================================================

print("=" * 75)
print("STEP 5C — GPS FIELD VALIDATION + DUPLICATE CLEANING")
print("=" * 75)

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive")

PROJECT_FOLDER = DRIVE_ROOT / "final year project"
STEP5_FOLDER = PROJECT_FOLDER / "Step 5"

# Preferred input filenames
INPUT_FILENAMES = [
    "final_field_candidates.csv",
    "sentinel2_availability.csv"
]

# ============================================================
# 2. FIND INPUT CSV FILE
# ============================================================

print("\n[1/10] Searching for input CSV files...")

INPUT_FILE = None

# First search the expected project folders.
SEARCH_FOLDERS = [
    STEP5_FOLDER / "text_and_csv_files",
    STEP5_FOLDER,
    PROJECT_FOLDER,
    DRIVE_ROOT
]

# Search the most specific folders first.
# Avoid scanning the same folder repeatedly.
searched = set()

for folder in SEARCH_FOLDERS:

    if not folder.exists():
        continue

    for filename in INPUT_FILENAMES:

        # Check directly inside the current folder first.
        candidate = folder / filename

        if candidate.is_file():
            INPUT_FILE = candidate
            break

    if INPUT_FILE is not None:
        break

# If not found directly, recursively search MyDrive.
if INPUT_FILE is None:

    print("File not found in expected folders.")
    print("Searching subfolders in Google Drive...")

    for filename in INPUT_FILENAMES:

        for candidate in DRIVE_ROOT.rglob(filename):

            # Skip duplicate paths.
            resolved = str(candidate.resolve())

            if resolved in searched:
                continue

            searched.add(resolved)

            if candidate.is_file():
                INPUT_FILE = candidate
                break

        if INPUT_FILE is not None:
            break

# Stop safely if no input exists.
if INPUT_FILE is None:

    print("\nERROR: Required input CSV was not found.")

    print("\nSearched filenames:")
    for filename in INPUT_FILENAMES:
        print(" -", filename)

    print("\nExpected project directory:")
    print(STEP5_FOLDER)

    print("\nCSV files currently found in Google Drive:")

    count = 0

    for candidate in DRIVE_ROOT.rglob("*.csv"):

        print(candidate)
        count += 1

        if count >= 100:
            print("Showing only the first 100 CSV files.")
            break

    if count == 0:
        print("No CSV files found in MyDrive.")

    raise FileNotFoundError(
        "\nNeither final_field_candidates.csv nor "
        "sentinel2_availability.csv exists in the searched "
        "Google Drive locations. Check the filenames or run "
        "the previous step that generates the required CSV."
    )

print("\nINPUT FILE FOUND:")
print(INPUT_FILE)

# ============================================================
# 3. LOAD INPUT DATA
# ============================================================

print("\n[2/10] Loading CSV...")

df = pd.read_csv(INPUT_FILE)

# Remove accidental spaces from column names.
df.columns = df.columns.astype(str).str.strip()

print("\nInput shape:", df.shape)

print("\nColumns found:")
print(df.columns.tolist())

# ============================================================
# 4. VALIDATE REQUIRED COLUMNS
# ============================================================

print("\n[3/10] Validating required columns...")

required_cols = [
    "field_id",
    "latitude",
    "longitude"
]

missing_cols = [
    col for col in required_cols
    if col not in df.columns
]

# Support a common alternative field identifier.
if "field_id" not in df.columns:

    if "clean_field_id" in df.columns:
        df["field_id"] = df["clean_field_id"]

    elif "field_name" in df.columns:
        df["field_id"] = df["field_name"]

if "field_id" not in df.columns:
    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

if missing_cols:

    raise ValueError(
        f"Required columns missing: {missing_cols}\n"
        f"Available columns: {df.columns.tolist()}\n"
        "Use the correct input CSV containing field IDs, "
        "latitude, and longitude."
    )

# Preserve original data and normalize coordinate columns.
df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

# ============================================================
# 5. IDENTIFY SENTINEL-2 IMAGE COUNTS
# ============================================================

print("\n[4/10] Checking Sentinel-2 image counts...")

# Some CSVs may use different column names.
possible_count_columns = [
    "sentinel2_image_count",
    "image_count",
    "sentinel_image_count",
    "available_images",
    "image_count_2months",
    "valid_image_count"
]

count_column = next(
    (
        col for col in possible_count_columns
        if col in df.columns
    ),
    None
)

if count_column is not None:

    df["sentinel2_image_count"] = pd.to_numeric(
        df[count_column],
        errors="coerce"
    )

    df["sentinel2_image_count"] = (
        df["sentinel2_image_count"]
        .fillna(0)
        .clip(lower=0)
    )

    print("Using image-count column:", count_column)

else:

    # Do not pretend that missing satellite information
    # means zero images were actually observed.
    df["sentinel2_image_count"] = 0

    print(
        "WARNING: No recognized Sentinel-2 image-count "
        "column was found."
    )

    print(
        "Satellite availability cannot be verified from "
        "this CSV. Image counts are initialized to zero."
    )

# ============================================================
# 6. VALIDATE GPS COORDINATES
# ============================================================

print("\n[5/10] Validating GPS coordinates...")

df["coordinate_valid"] = (
    df["latitude"].notna()
    & df["longitude"].notna()
    & df["latitude"].between(-90, 90)
    & df["longitude"].between(-180, 180)
)

# ============================================================
# 7. CHECK STUDY REGION
# ============================================================

print("\n[6/10] Checking study-region boundaries...")

# Existing project study region.
# Confirm these bounds match your actual project area.
LAT_MIN = 12.5
LAT_MAX = 14.0

LON_MIN = 78.5
LON_MAX = 80.5

df["region_status"] = "INVALID_COORDINATE"

valid_coord_mask = df["coordinate_valid"]

inside_region = (
    df["latitude"].between(LAT_MIN, LAT_MAX)
    & df["longitude"].between(LON_MIN, LON_MAX)
)

df.loc[
    valid_coord_mask & inside_region,
    "region_status"
] = "INSIDE_STUDY_REGION"

df.loc[
    valid_coord_mask & ~inside_region,
    "region_status"
] = "OUTSIDE_STUDY_REGION"

# ============================================================
# 8. DETECT NEAR-DUPLICATE COORDINATES
# ============================================================

print("\n[7/10] Detecting near-duplicate coordinates...")

DEDUP_RADIUS_METERS = 30
EARTH_RADIUS_METERS = 6_371_000

df["duplicate_group"] = -1

coords = df.loc[
    valid_coord_mask,
    ["latitude", "longitude"]
].to_numpy()

if len(coords) > 0:

    coords_rad = np.radians(coords)

    eps_radians = (
        DEDUP_RADIUS_METERS / EARTH_RADIUS_METERS
    )

    dbscan = DBSCAN(
        eps=eps_radians,
        min_samples=1,
        metric="haversine"
    )

    labels = dbscan.fit_predict(coords_rad)

    df.loc[
        valid_coord_mask,
        "duplicate_group"
    ] = labels + 1

df["duplicate_group"] = (
    pd.to_numeric(
        df["duplicate_group"],
        errors="coerce"
    )
    .fillna(-1)
    .astype(int)
)

# Count rows per group.
group_counts = (
    df.loc[df["duplicate_group"] != -1]
    .groupby("duplicate_group")
    .size()
)

df["duplicate_group_size"] = (
    df["duplicate_group"]
    .map(group_counts)
    .fillna(1)
    .astype(int)
)

df["duplicate_status"] = np.where(
    df["duplicate_group_size"] > 1,
    "NEAR_DUPLICATE_GROUP",
    "UNIQUE_FIELD"
)

# ============================================================
# 9. ASSIGN VALIDATION STATUS
# ============================================================

print("\n[8/10] Assigning validation statuses...")

def determine_status(row):

    if not row["coordinate_valid"]:
        return "INVALID_COORDINATE"

    if row["region_status"] == "OUTSIDE_STUDY_REGION":
        return "OUTSIDE_STUDY_REGION"

    if row["sentinel2_image_count"] <= 0:
        return "NO_VERIFIED_SENTINEL2_DATA"

    if row["duplicate_group_size"] > 1:
        return "NEAR_DUPLICATE_REVIEW"

    return "CLEAN"


df["validation_status"] = df.apply(
    determine_status,
    axis=1
)

# ============================================================
# 10. SAVE VALIDATION REPORTS
# ============================================================

print("\n[9/10] Saving validation reports...")

# Keep outputs separate from original input data.
OUTPUT_FOLDER = STEP5_FOLDER / "text_and_csv_files"

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

validation_file = (
    OUTPUT_FOLDER / "field_validation_report.csv"
)

duplicate_file = (
    OUTPUT_FOLDER / "near_duplicate_fields.csv"
)

clean_file = (
    OUTPUT_FOLDER / "clean_field_candidates.csv"
)

# Save complete validation report.
df.to_csv(
    validation_file,
    index=False
)

# Save near-duplicate report.
duplicate_report = (
    df.loc[df["duplicate_group_size"] > 1]
    .sort_values(
        by=["duplicate_group", "field_id"]
    )
    .copy()
)

duplicate_report.to_csv(
    duplicate_file,
    index=False
)

# Select valid coordinates inside the study region.
# Require positive Sentinel-2 image counts.
clean_base = df.loc[
    df["coordinate_valid"]
    & (df["region_status"] == "INSIDE_STUDY_REGION")
    & (df["sentinel2_image_count"] > 0)
].copy()

# Rank representatives by satellite image count.
clean_base = clean_base.sort_values(
    by=[
        "duplicate_group",
        "sentinel2_image_count"
    ],
    ascending=[
        True,
        False
    ]
)

# Keep one representative per duplicate group.
# Invalid-coordinate rows have duplicate_group = -1
# and cannot enter clean_base.
clean_fields = (
    clean_base
    .drop_duplicates(
        subset=["duplicate_group"],
        keep="first"
    )
    .reset_index(drop=True)
)

# Assign clean field IDs.
clean_fields["clean_field_id"] = [
    f"CLEAN_FIELD_{i:03d}"
    for i in range(1, len(clean_fields) + 1)
]

clean_fields.to_csv(
    clean_file,
    index=False
)

# ============================================================
# 11. PRINT FINAL SUMMARY
# ============================================================

print("\n[10/10] STEP 5C SUMMARY")

total_fields = len(df)

inside_count = (
    df["region_status"] == "INSIDE_STUDY_REGION"
).sum()

outside_count = (
    df["region_status"] == "OUTSIDE_STUDY_REGION"
).sum()

invalid_count = (
    ~df["coordinate_valid"]
).sum()

sentinel_available = (
    df["sentinel2_image_count"] > 0
).sum()

no_sentinel = (
    df["sentinel2_image_count"] <= 0
).sum()

near_duplicate_count = (
    df["duplicate_group_size"] > 1
).sum()

duplicate_group_count = (
    df.loc[
        df["duplicate_group_size"] > 1,
        "duplicate_group"
    ]
    .nunique()
)

print("\n" + "=" * 75)
print("STEP 5C — COMPLETED")
print("=" * 75)

print(f"Input file                 : {INPUT_FILE}")
print(f"Total records              : {total_fields}")
print(f"Inside study region        : {inside_count}")
print(f"Outside study region       : {outside_count}")
print(f"Invalid coordinates        : {invalid_count}")
print(f"Records with image count > 0: {sentinel_available}")
print(f"Records without image count: {no_sentinel}")
print(f"Near-duplicate records     : {near_duplicate_count}")
print(f"Near-duplicate groups      : {duplicate_group_count}")
print(f"Final clean fields         : {len(clean_fields)}")

print("\n" + "-" * 75)
print("OUTPUT FILES")
print("-" * 75)

print("\nValidation report:")
print(validation_file)

print("\nNear-duplicate report:")
print(duplicate_file)

print("\nClean field candidates:")
print(clean_file)

print("\n" + "-" * 75)
print("CLEAN FIELD PREVIEW")
print("-" * 75)

preview_cols = [
    "clean_field_id",
    "field_id",
    "latitude",
    "longitude",
    "sentinel2_image_count",
    "duplicate_group_size"
]

if len(clean_fields) > 0:

    display(clean_fields[preview_cols].head(30))

else:

    print(
        "No clean fields found. Check the study-region "
        "bounds and Sentinel-2 image-count information."
    )

print("\nIMPORTANT:")
print("1. Inspect the validation report.")
print("2. Confirm the study-region boundaries.")
print("3. Verify actual Sentinel-2 image availability.")
print("4. Inspect clean_field_candidates.csv before proceeding.")
print("\nSTEP 5C FINISHED.")

