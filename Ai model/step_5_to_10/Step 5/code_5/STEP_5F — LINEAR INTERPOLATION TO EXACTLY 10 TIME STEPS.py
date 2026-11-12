# ============================================================
# STEP_5F — LINEAR INTERPOLATION TO EXACTLY 10 TIME STEPS
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

INPUT_CSV = (
    SATELLITE_FOLDER /
    "sentinel2_timeseries_raw.csv"
)

OUTPUT_CSV = (
    SATELLITE_FOLDER /
    "sentinel2_timeseries.csv"
)

OUTPUT_NPY = (
    SATELLITE_FOLDER /
    "bilstm_sequences.npy"
)

REPORT_FILE = (
    SATELLITE_FOLDER.parent /
    "results" /
    "Step_5G_Interpolation_Report.txt"
)

CODE_FOLDER = (
    SATELLITE_FOLDER.parent /
    "code"
)

CODE_FILE = (
    CODE_FOLDER /
    "Step_5G_Linear_Interpolation.py"
)

# ------------------------------------------------------------
# CREATE FOLDERS
# ------------------------------------------------------------

REPORT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

CODE_FOLDER.mkdir(
    parents=True,
    exist_ok=True
)

# ------------------------------------------------------------
# LOAD RAW TIME SERIES
# ------------------------------------------------------------

df = pd.read_csv(
    INPUT_CSV
)

print("=" * 70)
print("STEP 5G — LINEAR INTERPOLATION")
print("=" * 70)

print("\nInput records:", len(df))

# ------------------------------------------------------------
# CHECK REQUIRED COLUMNS
# ------------------------------------------------------------

required_columns = [
    "field_id",
    "date",
    "NDVI",
    "NDRE",
    "GNDVI"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:

    raise ValueError(
        f"Missing columns: {missing_columns}"
    )

# ------------------------------------------------------------
# DATE CONVERSION
# ------------------------------------------------------------

df["date"] = pd.to_datetime(
    df["date"]
)

df = df.sort_values(
    [
        "field_id",
        "date"
    ]
).reset_index(
    drop=True
)

# ------------------------------------------------------------
# CHECK MISSING VALUES
# ------------------------------------------------------------

index_columns = [
    "NDVI",
    "NDRE",
    "GNDVI"
]

print("\nMissing values before interpolation:")

print(
    df[index_columns]
    .isna()
    .sum()
)

# ------------------------------------------------------------
# TARGET
# ------------------------------------------------------------

TARGET_STEPS = 10

fields = sorted(
    df["field_id"].unique()
)

print("\nFields found:", fields)

# ------------------------------------------------------------
# INTERPOLATION
# ------------------------------------------------------------

all_interpolated = []

sequence_list = []

for field_id in fields:

    field_df = df[
        df["field_id"] == field_id
    ].copy()

    field_df = field_df.sort_values(
        "date"
    ).reset_index(
        drop=True
    )

    print("\n" + "=" * 60)
    print(field_id)
    print("=" * 60)

    print(
        "Original observations:",
        len(field_df)
    )

    # --------------------------------------------------------
    # CONVERT DATES TO NUMERIC TIME
    # --------------------------------------------------------

    dates_numeric = (
        field_df["date"]
        .astype("int64")
        .to_numpy()
        / 1e9
    )

    # --------------------------------------------------------
    # HANDLE MISSING SATELLITE INDEX VALUES
    # --------------------------------------------------------

    for index_name in index_columns:

        field_df[index_name] = pd.to_numeric(
            field_df[index_name],
            errors="coerce"
        )

        missing_before = field_df[index_name].isna().sum()

        if missing_before > 0:

            print(
                f"{index_name}: "
                f"{missing_before} missing value(s) found"
            )

            field_df[index_name] = (
                field_df[index_name]
                .interpolate(
                    method="linear",
                    limit_direction="both"
                )
            )

        missing_after = field_df[index_name].isna().sum()

        if missing_after > 0:

            raise ValueError(
                f"{field_id} — {index_name} "
                f"still contains NaN values after interpolation."
            )

    # --------------------------------------------------------
    # 10 EVENLY SPACED TIME POSITIONS
    # BETWEEN FIRST AND LAST REAL OBSERVATION
    # --------------------------------------------------------

    target_time = np.linspace(
        dates_numeric.min(),
        dates_numeric.max(),
        TARGET_STEPS
    )

    # --------------------------------------------------------
    # INTERPOLATE EACH INDEX
    # --------------------------------------------------------

    interpolated_values = []

    for index_name in index_columns:

        values = (
            field_df[index_name]
            .astype(float)
            .to_numpy()
        )

        interpolated = np.interp(
            target_time,
            dates_numeric,
            values
        )

        interpolated_values.append(
            interpolated
        )

    # Shape:
    # 10 × 3

    sequence = np.column_stack(
        interpolated_values
    )

    sequence_list.append(
        sequence.astype(np.float32)
    )

    # --------------------------------------------------------
    # CREATE OUTPUT ROWS
    # --------------------------------------------------------

    target_dates = pd.to_datetime(
        target_time,
        unit="s"
    )

    for step in range(
        TARGET_STEPS
    ):

        all_interpolated.append({

            "field_id":
                field_id,

            "time_step":
                step + 1,

            "date":
                target_dates[step]
                .strftime("%Y-%m-%d"),

            "NDVI":
                round(
                    float(
                        sequence[step, 0]
                    ),
                    6
                ),

            "NDRE":
                round(
                    float(
                        sequence[step, 1]
                    ),
                    6
                ),

            "GNDVI":
                round(
                    float(
                        sequence[step, 2]
                    ),
                    6
                )
        })

    print(
        "Interpolated sequence shape:",
        sequence.shape
    )

# ------------------------------------------------------------
# CREATE FINAL DATAFRAME
# ------------------------------------------------------------

final_df = pd.DataFrame(
    all_interpolated
)

# ------------------------------------------------------------
# CREATE FINAL NUMPY TENSOR
# ------------------------------------------------------------

X_satellite = np.stack(
    sequence_list,
    axis=0
).astype(
    np.float32
)

print("\n" + "=" * 70)
print("FINAL SATELLITE TENSOR")
print("=" * 70)

print(
    "Shape:",
    X_satellite.shape
)

print(
    "Expected:",
    f"({len(fields)}, 10, 3)"
)

# ------------------------------------------------------------
# CHECK SHAPE
# ------------------------------------------------------------

expected_shape = (
    len(fields),
    TARGET_STEPS,
    3
)

if X_satellite.shape != expected_shape:

    raise ValueError(
        f"Unexpected tensor shape: "
        f"{X_satellite.shape}"
    )

# ------------------------------------------------------------
# CHECK NaN / INF
# ------------------------------------------------------------

nan_count = np.isnan(
    X_satellite
).sum()

inf_count = np.isinf(
    X_satellite
).sum()

print(
    "\nNaN values:",
    nan_count
)

print(
    "Infinite values:",
    inf_count
)

if nan_count != 0:

    raise ValueError(
        "NaN values found!"
    )

if inf_count != 0:

    raise ValueError(
        "Infinite values found!"
    )

# ------------------------------------------------------------
# SAVE FINAL CSV
# ------------------------------------------------------------

final_df.to_csv(
    OUTPUT_CSV,
    index=False
)

# ------------------------------------------------------------
# SAVE NUMPY TENSOR
# ------------------------------------------------------------

np.save(
    OUTPUT_NPY,
    X_satellite
)

# ------------------------------------------------------------
# SAVE FIELD LOCATIONS COPY
# ------------------------------------------------------------

FINAL_FIELDS_INPUT = (
    SATELLITE_FOLDER /
    "clean_field_candidates_renamed.csv"
)

FIELD_LOCATIONS_OUTPUT = (
    SATELLITE_FOLDER /
    "field_locations.csv"
)

field_locations = pd.read_csv(
    FINAL_FIELDS_INPUT
)

field_locations[
    [
        "field_id",
        "latitude",
        "longitude"
    ]
].to_csv(
    FIELD_LOCATIONS_OUTPUT,
    index=False
)

# ------------------------------------------------------------
# CREATE REPORT
# ------------------------------------------------------------

report_lines = [

    "STEP 5G — LINEAR INTERPOLATION REPORT",
    "=" * 60,
    "",

    f"Input CSV: {INPUT_CSV}",
    f"Output CSV: {OUTPUT_CSV}",
    f"Output NPY: {OUTPUT_NPY}",
    "",

    f"Number of fields: {len(fields)}",
    f"Target time steps: {TARGET_STEPS}",
    f"Features per timestep: 3",
    "",

    f"Final tensor shape: {X_satellite.shape}",
    f"NaN values: {nan_count}",
    f"Infinite values: {inf_count}",
    "",

    "Features:",
    "1. NDVI",
    "2. NDRE",
    "3. GNDVI",
    "",

    "Interpolation method:",
    "Linear interpolation between first and last",
    "real Sentinel-2 observations for each field.",
    "",

    "Missing index values were interpolated before",
    "the final 10-step temporal interpolation.",
    "",

    "Original raw satellite values were preserved.",
    "",

    "STEP 5G COMPLETE"
]

with open(
    REPORT_FILE,
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "\n".join(report_lines)
    )

# ------------------------------------------------------------
# SAVE CODE BACKUP
# ------------------------------------------------------------

try:

    code_text = (
        get_ipython()
        .history_manager
        .input_hist_raw[-1]
    )

    with open(
        CODE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(code_text)

    print(
        "\nCode backup saved:"
    )

    print(
        CODE_FILE
    )

except Exception as e:

    print(
        "\n⚠️ Code backup could not be saved:",
        e
    )

# ------------------------------------------------------------
# FINAL OUTPUT
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 5G — COMPLETE")
print("=" * 70)

print(
    "\nFinal CSV:"
)

print(
    OUTPUT_CSV
)

print(
    "\nFinal NumPy tensor:"
)

print(
    OUTPUT_NPY
)

print(
    "\nField locations:"
)

print(
    FIELD_LOCATIONS_OUTPUT
)

print(
    "\nReport:"
)

print(
    REPORT_FILE
)

print(
    "\nFinal tensor shape:",
    X_satellite.shape
)

print(
    "\n✅ STEP 5G LINEAR INTERPOLATION COMPLETE"
)