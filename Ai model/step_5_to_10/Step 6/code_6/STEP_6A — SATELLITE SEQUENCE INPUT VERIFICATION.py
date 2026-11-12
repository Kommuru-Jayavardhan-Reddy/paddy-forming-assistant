# ============================================================
# STEP 6A — SATELLITE SEQUENCE INPUT VERIFICATION
# ============================================================

import os
import numpy as np

# ============================================================
# 1. GOOGLE DRIVE
# ============================================================

from google.colab import drive

drive.mount("/content/drive")

# ============================================================
# 2. FIND SATELLITE SEQUENCE FILE
# ============================================================

DRIVE_ROOT = "/content/drive/MyDrive"
TARGET_FILE = "bilstm_sequences.npy"

print("=" * 70)
print("STEP 6A — SATELLITE SEQUENCE INPUT VERIFICATION")
print("=" * 70)

print("\nSearching for:", TARGET_FILE)

found_files = []

for root, dirs, files in os.walk(DRIVE_ROOT):

    if TARGET_FILE in files:

        found_files.append(
            os.path.join(root, TARGET_FILE)
        )

if len(found_files) == 0:

    raise FileNotFoundError(
        "\n❌ bilstm_sequences.npy was not found in Google Drive."
    )

print(f"\n✅ Found {len(found_files)} file(s):")

for i, path in enumerate(found_files, start=1):

    print(f"{i}. {path}")

# ============================================================
# 3. SELECT FILE
# ============================================================

if len(found_files) == 1:

    DATA_PATH = found_files[0]

else:

    # Prefer the Real_world_test / Step 5 version
    preferred = [
        p for p in found_files
        if "Real_world_test" in p
        and "Step 5" in p
    ]

    if len(preferred) == 1:

        DATA_PATH = preferred[0]

    else:

        DATA_PATH = found_files[0]

print("\n" + "-" * 70)
print("SELECTED FILE")
print("-" * 70)

print(DATA_PATH)

# ============================================================
# 4. FILE CHECK
# ============================================================

if not os.path.exists(DATA_PATH):

    raise FileNotFoundError(
        f"\n❌ File not found:\n{DATA_PATH}"
    )

print("\n✅ File exists")

# ============================================================
# 5. LOAD SATELLITE SEQUENCES
# ============================================================

print("\n" + "-" * 70)
print("LOADING SATELLITE SEQUENCES")
print("-" * 70)

X_sat = np.load(DATA_PATH)

print("\n✅ Satellite sequence file loaded")

print("Shape :", X_sat.shape)
print("Dtype :", X_sat.dtype)

# ============================================================
# 6. BASIC DIMENSION CHECK
# ============================================================

print("\n" + "-" * 70)
print("DIMENSION VERIFICATION")
print("-" * 70)

dimension_ok = X_sat.ndim == 3

if dimension_ok:

    print("✅ Input is 3-dimensional")

else:

    print("❌ Input must be 3-dimensional")

# ============================================================
# 7. EXTRACT ACTUAL SHAPE
# ============================================================

if X_sat.ndim == 3:

    num_sequences = X_sat.shape[0]
    sequence_length = X_sat.shape[1]
    num_features = X_sat.shape[2]

else:

    num_sequences = 0
    sequence_length = 0
    num_features = 0

print("\nActual input structure:")

print("Number of sequences :", num_sequences)
print("Sequence length     :", sequence_length)
print("Number of features  :", num_features)

# ============================================================
# 8. EXPECTED BiLSTM INPUT FORMAT
# ============================================================

print("\n" + "-" * 70)
print("BiLSTM INPUT FORMAT")
print("-" * 70)

print("\nExpected:")
print("[batch, sequence_length, features]")

print("\nRequired:")
print("sequence_length = 10")
print("features        = 3")
print("batch           = variable")

# ============================================================
# 9. SHAPE VERIFICATION
# ============================================================

sequence_ok = (
    X_sat.ndim == 3
    and sequence_length == 10
)

feature_ok = (
    X_sat.ndim == 3
    and num_features == 3
)

batch_ok = (
    X_sat.ndim == 3
    and num_sequences > 0
)

print("\nShape validation:")

print(
    "Batch dimension    : "
    + ("✅ PASS" if batch_ok else "❌ FAIL")
)

print(
    "Sequence length=10 : "
    + ("✅ PASS" if sequence_ok else "❌ FAIL")
)

print(
    "Features=3         : "
    + ("✅ PASS" if feature_ok else "❌ FAIL")
)

# ============================================================
# 10. DATA QUALITY
# ============================================================

print("\n" + "-" * 70)
print("DATA QUALITY VERIFICATION")
print("-" * 70)

nan_count = np.isnan(X_sat).sum()
inf_count = np.isinf(X_sat).sum()

nan_ok = nan_count == 0
inf_ok = inf_count == 0

print("NaN count :", nan_count)
print("Inf count :", inf_count)

print(
    "NaN check : "
    + ("✅ PASS" if nan_ok else "❌ FAIL")
)

print(
    "Inf check : "
    + ("✅ PASS" if inf_ok else "❌ FAIL")
)

# ============================================================
# 11. FEATURE ORDER
# ============================================================

print("\n" + "-" * 70)
print("FEATURE ORDER")
print("-" * 70)

print("Feature 1 → NDVI")
print("Feature 2 → NDRE")
print("Feature 3 → GNDVI")

# ============================================================
# 12. FEATURE-WISE STATISTICS
# ============================================================

print("\n" + "-" * 70)
print("FEATURE-WISE STATISTICS")
print("-" * 70)

if X_sat.ndim == 3 and num_features == 3:

    feature_names = [
        "NDVI",
        "NDRE",
        "GNDVI"
    ]

    for i, feature_name in enumerate(feature_names):

        feature_data = X_sat[:, :, i]

        print(f"\n{feature_name}")

        print(
            f"  Minimum : {feature_data.min():.6f}"
        )

        print(
            f"  Maximum : {feature_data.max():.6f}"
        )

        print(
            f"  Mean    : {feature_data.mean():.6f}"
        )

        print(
            f"  Std     : {feature_data.std():.6f}"
        )

# ============================================================
# 13. OVERALL STATISTICS
# ============================================================

print("\n" + "-" * 70)
print("OVERALL STATISTICS")
print("-" * 70)

print(f"Minimum : {X_sat.min():.6f}")
print(f"Maximum : {X_sat.max():.6f}")
print(f"Mean    : {X_sat.mean():.6f}")
print(f"Std     : {X_sat.std():.6f}")

# ============================================================
# 14. DATA VARIATION
# ============================================================

print("\n" + "-" * 70)
print("DATA VARIATION CHECK")
print("-" * 70)

variation_ok = X_sat.std() > 0

if variation_ok:

    print("✅ Data contains meaningful variation")

else:

    print("❌ All values are identical")

# ============================================================
# 15. RANGE CHECK
# ============================================================

print("\n" + "-" * 70)
print("FEATURE RANGE CHECK")
print("-" * 70)

print(
    "NDVI range : "
    f"{X_sat[:, :, 0].min():.6f} → "
    f"{X_sat[:, :, 0].max():.6f}"
)

print(
    "NDRE range : "
    f"{X_sat[:, :, 1].min():.6f} → "
    f"{X_sat[:, :, 1].max():.6f}"
)

print(
    "GNDVI range: "
    f"{X_sat[:, :, 2].min():.6f} → "
    f"{X_sat[:, :, 2].max():.6f}"
)

# ============================================================
# 16. SAMPLE SEQUENCE
# ============================================================

print("\n" + "-" * 70)
print("SAMPLE SEQUENCE — FIRST FIELD")
print("-" * 70)

if X_sat.ndim == 3 and num_sequences > 0:

    print(
        "\nTimestep     NDVI          NDRE          GNDVI"
    )

    print("-" * 55)

    for t in range(sequence_length):

        print(
            f"{t + 1:<12}"
            f"{X_sat[0, t, 0]:<14.6f}"
            f"{X_sat[0, t, 1]:<14.6f}"
            f"{X_sat[0, t, 2]:<14.6f}"
        )

# ============================================================
# 17. FINAL VALIDATION
# ============================================================

all_checks_passed = (
    dimension_ok
    and batch_ok
    and sequence_ok
    and feature_ok
    and nan_ok
    and inf_ok
    and variation_ok
)

# ============================================================
# FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("STEP 6A — FINAL RESULT")
print("=" * 70)

print("\nValidation summary:")

print(
    f"3D Input            : "
    f"{'✅ PASS' if dimension_ok else '❌ FAIL'}"
)

print(
    f"Batch Dimension     : "
    f"{'✅ PASS' if batch_ok else '❌ FAIL'}"
)

print(
    f"Sequence Length=10  : "
    f"{'✅ PASS' if sequence_ok else '❌ FAIL'}"
)

print(
    f"Features=3          : "
    f"{'✅ PASS' if feature_ok else '❌ FAIL'}"
)

print(
    f"No NaN              : "
    f"{'✅ PASS' if nan_ok else '❌ FAIL'}"
)

print(
    f"No Inf              : "
    f"{'✅ PASS' if inf_ok else '❌ FAIL'}"
)

print(
    f"Data Variation      : "
    f"{'✅ PASS' if variation_ok else '❌ FAIL'}"
)

# ============================================================
# PASS / FAIL
# ============================================================

if all_checks_passed:

    print("\n" + "=" * 70)
    print("✅ STEP 6A PASSED")
    print("=" * 70)

    print("\nSatellite input is READY for Step 6B.")

    print("\nActual input:")
    print(
        f"X_sat = [{num_sequences}, "
        f"{sequence_length}, "
        f"{num_features}]"
    )

    print("\nBiLSTM will receive:")
    print(
        f"[batch={num_sequences}, "
        f"sequence_length=10, "
        f"features=3]"
    )

    print("\nExpected BiLSTM embedding:")
    print("[batch, 256]")

else:

    print("\n" + "=" * 70)
    print("❌ STEP 6A FAILED")
    print("=" * 70)

    print("\nDo NOT continue to Step 6B.")
    print("Fix the failed validation first.")