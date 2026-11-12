# ============================================================
# STEP 5H — FINAL SATELLITE PIPELINE VERIFICATION
# ============================================================

from pathlib import Path
import pandas as pd
import numpy as np

# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SATELLITE_FOLDER = Path(
    "/content/drive/MyDrive/final year project/Real_world_test/Step 5"
)

RESULTS_FOLDER = (
    SATELLITE_FOLDER.parent / "results"
)

REPORT_FILE = (
    RESULTS_FOLDER /
    "Step_5H_Final_Verification_Report.txt"
)

# ------------------------------------------------------------
# FILES TO VERIFY
# ------------------------------------------------------------

FIELD_FILE = (
    SATELLITE_FOLDER /
    "field_locations.csv"
)

TIMESERIES_FILE = (
    SATELLITE_FOLDER /
    "sentinel2_timeseries.csv"
)

NPY_FILE = (
    SATELLITE_FOLDER /
    "bilstm_sequences.npy"
)

RAW_TIMESERIES_FILE = (
    SATELLITE_FOLDER /
    "sentinel2_timeseries_raw.csv"
)

# ------------------------------------------------------------
# START
# ------------------------------------------------------------

print("=" * 70)
print("STEP 5H — FINAL SATELLITE PIPELINE VERIFICATION")
print("=" * 70)

errors = []

# ------------------------------------------------------------
# 1. CHECK FILE EXISTENCE
# ------------------------------------------------------------

print("\n1. FILE EXISTENCE CHECK")
print("-" * 50)

files_to_check = {
    "field_locations.csv": FIELD_FILE,
    "sentinel2_timeseries.csv": TIMESERIES_FILE,
    "bilstm_sequences.npy": NPY_FILE,
    "sentinel2_timeseries_raw.csv": RAW_TIMESERIES_FILE
}

for name, path in files_to_check.items():

    exists = path.exists()

    print(
        f"{name:<35} : "
        f"{'✅ EXISTS' if exists else '❌ MISSING'}"
    )

    if not exists:

        errors.append(
            f"Missing file: {name}"
        )

# ------------------------------------------------------------
# 2. LOAD FIELD LOCATIONS
# ------------------------------------------------------------

print("\n2. FIELD LOCATION CHECK")
print("-" * 50)

fields = pd.DataFrame()

if FIELD_FILE.exists():

    fields = pd.read_csv(
        FIELD_FILE
    )

    print(
        "Number of fields:",
        len(fields)
    )

    print(
        "Field IDs:",
        list(fields["field_id"])
    )

    # --------------------------------------------------------
    # CHECK CONTINUOUS FIELD IDs
    # --------------------------------------------------------

    expected_fields = [
        f"FIELD_{i:02d}"
        for i in range(
            1,
            len(fields) + 1
        )
    ]

    actual_fields = (
        fields["field_id"]
        .astype(str)
        .tolist()
    )

    if actual_fields == expected_fields:

        print(
            "Field IDs: ✅ CORRECT"
        )

    else:

        print(
            "Field IDs: ❌ INCORRECT"
        )

        errors.append(
            "Field IDs are not continuous from FIELD_01 onward"
        )

# ------------------------------------------------------------
# 3. LOAD FINAL TIME SERIES
# ------------------------------------------------------------

print("\n3. FINAL CSV CHECK")
print("-" * 50)

ts = pd.DataFrame()

if TIMESERIES_FILE.exists():

    ts = pd.read_csv(
        TIMESERIES_FILE
    )

    print(
        "Total rows:",
        len(ts)
    )

    # --------------------------------------------------------
    # EXPECTED ROW COUNT
    # --------------------------------------------------------

    expected_rows = (
        len(fields) * 10
    )

    print(
        "Expected rows:",
        expected_rows
    )

    if len(ts) == expected_rows:

        print(
            f"Row count: ✅ {expected_rows}"
        )

    else:

        print(
            "Row count: ❌"
        )

        errors.append(
            f"Expected {expected_rows} rows, found {len(ts)}"
        )

    # --------------------------------------------------------
    # CHECK REQUIRED COLUMNS
    # --------------------------------------------------------

    required_columns = [
        "field_id",
        "time_step",
        "date",
        "NDVI",
        "NDRE",
        "GNDVI"
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in ts.columns
    ]

    if len(missing_columns) == 0:

        print(
            "Required columns: ✅"
        )

    else:

        print(
            "Missing columns:",
            missing_columns
        )

        errors.append(
            f"Missing columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # CHECK 10 TIME STEPS PER FIELD
    # --------------------------------------------------------

    step_counts = (
        ts.groupby("field_id")
        ["time_step"]
        .count()
    )

    print("\nTime steps per field:")

    print(
        step_counts
    )

    if (
        len(step_counts) == len(fields)
        and all(step_counts == 10)
    ):

        print(
            "10 steps per field: ✅"
        )

    else:

        print(
            "10 steps per field: ❌"
        )

        errors.append(
            "Not every field contains exactly 10 time steps"
        )

    # --------------------------------------------------------
    # CHECK DUPLICATES
    # --------------------------------------------------------

    duplicates = ts.duplicated().sum()

    print(
        "\nDuplicate rows:",
        duplicates
    )

    if duplicates == 0:

        print(
            "Duplicates: ✅ NONE"
        )

    else:

        print(
            "Duplicates: ⚠️ FOUND"
        )

        errors.append(
            f"Duplicate rows found: {duplicates}"
        )

# ------------------------------------------------------------
# 4. CHECK VEGETATION INDEX VALUES
# ------------------------------------------------------------

print("\n4. VEGETATION INDEX CHECK")
print("-" * 50)

if TIMESERIES_FILE.exists():

    index_columns = [
        "NDVI",
        "NDRE",
        "GNDVI"
    ]

    nan_count = (
        ts[index_columns]
        .isna()
        .sum()
        .sum()
    )

    inf_count = np.isinf(
        ts[index_columns]
        .to_numpy()
    ).sum()

    print(
        "NaN values:",
        nan_count
    )

    print(
        "Infinite values:",
        inf_count
    )

    if nan_count == 0:

        print(
            "NaN check: ✅"
        )

    else:

        print(
            "NaN check: ❌"
        )

        errors.append(
            "NaN values found in final time series"
        )

    if inf_count == 0:

        print(
            "Infinite check: ✅"
        )

    else:

        print(
            "Infinite check: ❌"
        )

        errors.append(
            "Infinite values found in final time series"
        )

# ------------------------------------------------------------
# 5. LOAD NUMPY TENSOR
# ------------------------------------------------------------

print("\n5. NUMPY TENSOR CHECK")
print("-" * 50)

X_satellite = None

if NPY_FILE.exists():

    X_satellite = np.load(
        NPY_FILE
    )

    print(
        "Tensor shape:",
        X_satellite.shape
    )

    # --------------------------------------------------------
    # EXPECTED SHAPE
    # --------------------------------------------------------

    expected_shape = (
        len(fields),
        10,
        3
    )

    print(
        "Expected shape:",
        expected_shape
    )

    if X_satellite.shape == expected_shape:

        print(
            "Tensor shape: ✅ CORRECT"
        )

    else:

        print(
            "Tensor shape: ❌ INCORRECT"
        )

        errors.append(
            f"Wrong tensor shape: {X_satellite.shape}"
        )

    # --------------------------------------------------------
    # CHECK TENSOR NaN / INF
    # --------------------------------------------------------

    tensor_nan = np.isnan(
        X_satellite
    ).sum()

    tensor_inf = np.isinf(
        X_satellite
    ).sum()

    print(
        "Tensor NaN:",
        tensor_nan
    )

    print(
        "Tensor Infinite:",
        tensor_inf
    )

    if tensor_nan == 0 and tensor_inf == 0:

        print(
            "Tensor values: ✅ VALID"
        )

    else:

        print(
            "Tensor values: ❌ INVALID"
        )

        errors.append(
            "NaN or Inf found in NumPy tensor"
        )

# ------------------------------------------------------------
# 6. VERIFY FIELD/TENSOR MATCH
# ------------------------------------------------------------

print("\n6. FIELD/TENSOR CONSISTENCY")
print("-" * 50)

if (
    TIMESERIES_FILE.exists()
    and NPY_FILE.exists()
):

    unique_fields = (
        ts["field_id"]
        .nunique()
    )

    tensor_fields = (
        X_satellite.shape[0]
    )

    field_location_count = len(
        fields
    )

    print(
        "Field locations:",
        field_location_count
    )

    print(
        "CSV fields:",
        unique_fields
    )

    print(
        "Tensor fields:",
        tensor_fields
    )

    if (
        unique_fields
        == tensor_fields
        == field_location_count
    ):

        print(
            "Field consistency: ✅"
        )

    else:

        print(
            "Field consistency: ❌"
        )

        errors.append(
            "CSV, field locations and tensor field count mismatch"
        )

# ------------------------------------------------------------
# 7. VERIFY FIELD IDs BETWEEN FILES
# ------------------------------------------------------------

print("\n7. FIELD ID CONSISTENCY")
print("-" * 50)

if (
    FIELD_FILE.exists()
    and TIMESERIES_FILE.exists()
):

    field_location_ids = set(
        fields["field_id"]
    )

    timeseries_ids = set(
        ts["field_id"]
    )

    if field_location_ids == timeseries_ids:

        print(
            "Field IDs between files: ✅ MATCH"
        )

    else:

        print(
            "Field IDs between files: ❌ MISMATCH"
        )

        errors.append(
            "Field IDs mismatch between field_locations.csv and sentinel2_timeseries.csv"
        )

# ------------------------------------------------------------
# 8. FINAL RESULT
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 5H — FINAL RESULT")
print("=" * 70)

if len(errors) == 0:

    status = "PASS"

    print(
        "\n🎉 STEP 5 SATELLITE PIPELINE VERIFIED SUCCESSFULLY"
    )

    print(
        "\nFinal tensor:",
        X_satellite.shape
    )

    print(
        "Fields:",
        len(fields)
    )

    print(
        "Time steps per field:",
        "10"
    )

    print(
        "Features:",
        "NDVI, NDRE, GNDVI"
    )

    print(
        "Final CSV rows:",
        len(ts)
    )

    print(
        "NaN:",
        "0"
    )

    print(
        "Infinite:",
        "0"
    )

else:

    status = "FAIL"

    print(
        "\n❌ STEP 5 VERIFICATION FAILED"
    )

    print(
        "\nProblems found:"
    )

    for error in errors:

        print(
            " -",
            error
        )

# ------------------------------------------------------------
# SAVE REPORT
# ------------------------------------------------------------

report_lines = [

    "STEP 5H — FINAL SATELLITE PIPELINE VERIFICATION",
    "=" * 60,
    "",

    f"Status: {status}",
    "",

    f"Field file: {FIELD_FILE}",
    f"Time-series file: {TIMESERIES_FILE}",
    f"NumPy tensor: {NPY_FILE}",
    "",

    f"Fields: {len(fields) if FIELD_FILE.exists() else 'N/A'}",
    f"Final CSV rows: {len(ts) if TIMESERIES_FILE.exists() else 'N/A'}",
    f"Tensor shape: {X_satellite.shape if NPY_FILE.exists() else 'N/A'}",
    "",

    f"Errors: {len(errors)}"
]

if errors:

    report_lines.append("")

    report_lines.append(
        "ERRORS:"
    )

    for error in errors:

        report_lines.append(
            f"- {error}"
        )

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(report_lines)
    )

print(
    "\nVerification report saved:"
)

print(
    REPORT_FILE
)

print(
    "\n" + "=" * 70
)

if status == "PASS":

    print(
        "✅ STEP 5 COMPLETE"
    )

else:

    print(
        "⚠️ STEP 5 NEEDS CORRECTION"
    )