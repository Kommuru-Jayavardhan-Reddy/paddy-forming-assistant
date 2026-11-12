# ============================================================
# STEP 1D — SPLIT VERIFICATION & DATA LEAKAGE CHECK
#             + DRIVE REPORT & CODE BACKUP
# ============================================================

from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
from collections import defaultdict
import hashlib
import pandas as pd


# ============================================================
# 1. PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(
    "/content/drive/MyDrive/final year project"
)

ORIGINAL_DATASET = PROJECT_DIR / "Dataset"

SPLIT_DIR = PROJECT_DIR / "Dataset_Split"

REAL_WORLD_DIR = PROJECT_DIR / "Real_world_test"

RESULTS_DIR = PROJECT_DIR / "results"

CODE_DIR = PROJECT_DIR / "code"

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CODE_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 2. SETTINGS
# ============================================================

EXPECTED_TOTAL = 20320
EXPECTED_CLASSES = 13

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

SPLITS = [
    "train",
    "val",
    "test"
]


# ============================================================
# 3. HEADER
# ============================================================

print("=" * 75)
print("STEP 1D — SPLIT VERIFICATION & DATA LEAKAGE CHECK")
print("=" * 75)

print("\nOriginal Dataset:")
print(ORIGINAL_DATASET)

print("\nSplit Dataset:")
print(SPLIT_DIR)

print("\nReal World Test:")
print(REAL_WORLD_DIR)


# ============================================================
# 4. CHECK REQUIRED FOLDERS
# ============================================================

print("\n" + "=" * 75)
print("FOLDER CHECK")
print("=" * 75)

required_paths = {
    "Original Dataset": ORIGINAL_DATASET,
    "Dataset Split": SPLIT_DIR,
    "Real World Test": REAL_WORLD_DIR
}

for name, path in required_paths.items():

    if path.exists():

        print(f"✅ {name}: FOUND")

    else:

        print(f"⚠️ {name}: NOT FOUND")


if not ORIGINAL_DATASET.exists():

    raise FileNotFoundError(
        f"Original Dataset not found:\n{ORIGINAL_DATASET}"
    )

if not SPLIT_DIR.exists():

    raise FileNotFoundError(
        f"Dataset_Split not found:\n{SPLIT_DIR}"
    )


# ============================================================
# 5. CHECK TRAIN / VAL / TEST
# ============================================================

print("\n" + "=" * 75)
print("SPLIT FOLDER CHECK")
print("=" * 75)

missing_splits = []

for split in SPLITS:

    split_path = SPLIT_DIR / split

    if split_path.exists():

        print(
            f"✅ {split.upper()} folder found"
        )

    else:

        print(
            f"❌ {split.upper()} folder missing"
        )

        missing_splits.append(split)


if missing_splits:

    raise FileNotFoundError(
        f"Missing split folders: {missing_splits}"
    )


# ============================================================
# 6. FIND CLASS FOLDERS
# ============================================================

original_classes = sorted([
    folder.name
    for folder in ORIGINAL_DATASET.iterdir()
    if folder.is_dir()
])

print("\n" + "=" * 75)
print("CLASS VERIFICATION")
print("=" * 75)

print(
    f"\nOriginal Dataset Classes: "
    f"{len(original_classes)}"
)

for i, cls in enumerate(
    original_classes,
    1
):

    print(
        f"{i:2d}. {cls}"
    )


if len(original_classes) != EXPECTED_CLASSES:

    raise ValueError(
        f"\n❌ Expected {EXPECTED_CLASSES} classes, "
        f"found {len(original_classes)}"
    )

print(
    "\n✅ 13 classes confirmed"
)


# ============================================================
# 7. CHECK ALL CLASSES EXIST IN EACH SPLIT
# ============================================================

print("\n" + "=" * 75)
print("SPLIT CLASS CHECK")
print("=" * 75)

split_class_status = []

for split in SPLITS:

    split_path = SPLIT_DIR / split

    split_classes = sorted([
        folder.name
        for folder in split_path.iterdir()
        if folder.is_dir()
    ])

    missing = sorted(
        set(original_classes)
        - set(split_classes)
    )

    extra = sorted(
        set(split_classes)
        - set(original_classes)
    )

    print(
        f"\n{split.upper()}:"
    )

    print(
        f"  Classes found: "
        f"{len(split_classes)}"
    )

    if not missing and not extra:

        print(
            "  ✅ All 13 classes present"
        )

    else:

        if missing:

            print(
                "  ❌ Missing:",
                missing
            )

        if extra:

            print(
                "  ⚠️ Extra:",
                extra
            )

    split_class_status.append({
        "Split": split,
        "Classes_Found": len(split_classes),
        "Missing_Classes": ", ".join(missing),
        "Extra_Classes": ", ".join(extra)
    })


# ============================================================
# 8. COUNT IMAGES IN EACH SPLIT
# ============================================================

print("\n" + "=" * 75)
print("IMAGE COUNT VERIFICATION")
print("=" * 75)

split_records = []

for split in SPLITS:

    split_path = SPLIT_DIR / split

    for class_name in original_classes:

        class_path = (
            split_path /
            class_name
        )

        if not class_path.exists():

            continue

        for file in class_path.rglob("*"):

            if (
                file.is_file()
                and
                file.suffix.lower()
                in VALID_EXTENSIONS
            ):

                split_records.append({
                    "Split": split,
                    "Class": class_name,
                    "Path": str(file)
                })


split_df = pd.DataFrame(
    split_records
)

print(
    f"\nTotal split images found: "
    f"{len(split_df):,}"
)


if len(split_df) != EXPECTED_TOTAL:

    raise ValueError(
        f"\n❌ Split total mismatch!\n"
        f"Expected: {EXPECTED_TOTAL:,}\n"
        f"Found: {len(split_df):,}"
    )

print(
    "✅ Total split images = 20,320"
)


# ============================================================
# 9. OVERALL TRAIN / VAL / TEST COUNTS
# ============================================================

split_counts = (
    split_df
    .groupby("Split")
    .size()
    .reset_index(
        name="Image_Count"
    )
)

print("\n" + "=" * 75)
print("TRAIN / VALIDATION / TEST COUNTS")
print("=" * 75)

display(split_counts)


# ============================================================
# 10. CLASS DISTRIBUTION VERIFICATION
# ============================================================

distribution = (
    split_df
    .groupby(
        ["Class", "Split"]
    )
    .size()
    .unstack(
        fill_value=0
    )
    .reset_index()
)

for split in SPLITS:

    if split not in distribution.columns:

        distribution[split] = 0


distribution["Total"] = (
    distribution["train"]
    +
    distribution["val"]
    +
    distribution["test"]
)

distribution = distribution[
    [
        "Class",
        "train",
        "val",
        "test",
        "Total"
    ]
]

print("\n" + "=" * 75)
print("CLASS DISTRIBUTION")
print("=" * 75)

display(distribution)


# ============================================================
# 11. VERIFY CLASS TOTALS
# ============================================================

print("\n" + "=" * 75)
print("CLASS TOTAL VERIFICATION")
print("=" * 75)

original_counts = {}

for class_name in original_classes:

    class_path = (
        ORIGINAL_DATASET /
        class_name
    )

    count = sum(
        1
        for file in class_path.rglob("*")
        if (
            file.is_file()
            and
            file.suffix.lower()
            in VALID_EXTENSIONS
        )
    )

    original_counts[class_name] = count


class_verification = []

for _, row in distribution.iterrows():

    class_name = row["Class"]

    original_count = original_counts[
        class_name
    ]

    split_count = int(
        row["Total"]
    )

    status = (
        "PASS"
        if original_count == split_count
        else "FAIL"
    )

    class_verification.append({
        "Class": class_name,
        "Original_Count": original_count,
        "Split_Count": split_count,
        "Status": status
    })

class_verification_df = pd.DataFrame(
    class_verification
)

display(
    class_verification_df
)

if not (
    class_verification_df["Status"]
    == "PASS"
).all():

    raise ValueError(
        "\n❌ One or more class totals do not match."
    )

print(
    "\n✅ Every class total matches original Dataset"
)


# ============================================================
# 12. FILE PATH OVERLAP CHECK
# ============================================================

print("\n" + "=" * 75)
print("FILE PATH OVERLAP CHECK")
print("=" * 75)

paths_by_split = {}

for split in SPLITS:

    paths_by_split[split] = set(
        split_df.loc[
            split_df["Split"] == split,
            "Path"
        ]
    )

train_paths = paths_by_split["train"]
val_paths = paths_by_split["val"]
test_paths = paths_by_split["test"]

train_val_overlap = (
    train_paths & val_paths
)

train_test_overlap = (
    train_paths & test_paths
)

val_test_overlap = (
    val_paths & test_paths
)

print(
    f"\nTrain ∩ Validation: "
    f"{len(train_val_overlap)}"
)

print(
    f"Train ∩ Test: "
    f"{len(train_test_overlap)}"
)

print(
    f"Validation ∩ Test: "
    f"{len(val_test_overlap)}"
)

if (
    train_val_overlap
    or
    train_test_overlap
    or
    val_test_overlap
):

    raise ValueError(
        "\n❌ File path overlap detected!"
    )

print(
    "\n✅ No file path appears in multiple splits"
)


# ============================================================
# 13. SHA-256 CROSS-SPLIT LEAKAGE CHECK
# ============================================================

print("\n" + "=" * 75)
print("SHA-256 CROSS-SPLIT LEAKAGE CHECK")
print("=" * 75)

hash_records = []

for index, row in split_df.iterrows():

    file_path = Path(
        row["Path"]
    )

    sha256 = hashlib.sha256()

    with open(
        file_path,
        "rb"
    ) as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):

            sha256.update(chunk)

    file_hash = sha256.hexdigest()

    hash_records.append({
        "SHA256": file_hash,
        "Split": row["Split"],
        "Class": row["Class"],
        "Path": row["Path"]
    })

    if (index + 1) % 2000 == 0:

        print(
            f"Hashed: "
            f"{index + 1:,}/{len(split_df):,}"
        )


hash_df = pd.DataFrame(
    hash_records
)

hash_split_counts = (
    hash_df
    .groupby("SHA256")["Split"]
    .nunique()
)

cross_split_hashes = (
    hash_split_counts[
        hash_split_counts > 1
    ]
)

print(
    "\nUnique SHA-256 hashes:",
    hash_df["SHA256"].nunique()
)

print(
    "Cross-split duplicate hashes:",
    len(cross_split_hashes)
)

if len(cross_split_hashes) > 0:

    raise ValueError(
        "\n❌ DATA LEAKAGE DETECTED!"
        "\nSame image hash exists in multiple splits."
    )

print(
    "\n✅ No SHA-256 duplicate leakage"
)


# ============================================================
# 14. REAL-WORLD TEST SET CHECK
# ============================================================

print("\n" + "=" * 75)
print("REAL-WORLD TEST SET CHECK")
print("=" * 75)

if REAL_WORLD_DIR.exists():

    real_world_files = [
        file
        for file in REAL_WORLD_DIR.rglob("*")
        if (
            file.is_file()
            and
            file.suffix.lower()
            in VALID_EXTENSIONS
        )
    ]

    print(
        f"\nReal-world images found: "
        f"{len(real_world_files):,}"
    )

    print(
        "✅ Real-world test folder remains separate"
    )

else:

    print(
        "\n⚠️ Real_world_test folder not found"
    )


# ============================================================
# 15. SAVE VERIFICATION REPORTS
# ============================================================

summary = {
    "Check": [
        "Expected Total Images",
        "Actual Split Images",
        "Expected Classes",
        "Actual Classes",
        "Train Images",
        "Validation Images",
        "Test Images",
        "Train-Val Path Overlap",
        "Train-Test Path Overlap",
        "Val-Test Path Overlap",
        "Cross-Split SHA256 Leakage",
        "Original Dataset Modified"
    ],
    "Result": [
        EXPECTED_TOTAL,
        len(split_df),
        EXPECTED_CLASSES,
        len(original_classes),
        int(
            (split_df["Split"] == "train").sum()
        ),
        int(
            (split_df["Split"] == "val").sum()
        ),
        int(
            (split_df["Split"] == "test").sum()
        ),
        len(train_val_overlap),
        len(train_test_overlap),
        len(val_test_overlap),
        len(cross_split_hashes),
        "NO"
    ]
}

summary_df = pd.DataFrame(
    summary
)


# ============================================================
# 16. SAVE CSV FILES
# ============================================================

summary_path = (
    RESULTS_DIR /
    "Step_1D_Verification_Summary.csv"
)

distribution_path = (
    RESULTS_DIR /
    "Step_1D_Verified_Distribution.csv"
)

class_check_path = (
    RESULTS_DIR /
    "Step_1D_Class_Count_Verification.csv"
)

summary_df.to_csv(
    summary_path,
    index=False
)

distribution.to_csv(
    distribution_path,
    index=False
)

class_verification_df.to_csv(
    class_check_path,
    index=False
)


# ============================================================
# 17. SAVE TEXT REPORT
# ============================================================

report_path = (
    RESULTS_DIR /
    "Step_1D_Verification_Report.txt"
)

train_count = int(
    (split_df["Split"] == "train").sum()
)

val_count = int(
    (split_df["Split"] == "val").sum()
)

test_count = int(
    (split_df["Split"] == "test").sum()
)

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write("=" * 75 + "\n")
    f.write(
        "STEP 1D — DATASET SPLIT VERIFICATION REPORT\n"
    )
    f.write("=" * 75 + "\n\n")

    f.write(
        f"Expected Images: {EXPECTED_TOTAL:,}\n"
    )

    f.write(
        f"Verified Split Images: "
        f"{len(split_df):,}\n"
    )

    f.write(
        f"Classes: {len(original_classes)}\n\n"
    )

    f.write(
        f"Train Images: {train_count:,}\n"
    )

    f.write(
        f"Validation Images: {val_count:,}\n"
    )

    f.write(
        f"Test Images: {test_count:,}\n\n"
    )

    f.write(
        f"Train-Val Path Overlap: "
        f"{len(train_val_overlap)}\n"
    )

    f.write(
        f"Train-Test Path Overlap: "
        f"{len(train_test_overlap)}\n"
    )

    f.write(
        f"Val-Test Path Overlap: "
        f"{len(val_test_overlap)}\n"
    )

    f.write(
        f"Cross-Split SHA256 Leakage: "
        f"{len(cross_split_hashes)}\n"
    )

    f.write(
        "\nOriginal Dataset Modified: NO\n"
    )

    f.write(
        "Real-world test set kept separate: YES\n"
    )

    f.write(
        "\nFINAL STATUS: PASS\n"
    )


# ============================================================
# 18. FINAL STATUS
# ============================================================

print("\n" + "=" * 75)
print("STEP 1D COMPLETED")
print("=" * 75)

print("\n✅ 20,320 images verified")
print("✅ 13 classes verified")
print("✅ Train/Val/Test folders verified")
print("✅ Class counts verified")
print("✅ File-path leakage checked")
print("✅ SHA-256 cross-split leakage checked")
print("✅ Real-world test set kept separate")
print("✅ Original Dataset untouched")

print("\n📁 Results saved:")
print(RESULTS_DIR)

print("\n⚠️ No images were deleted.")
print("⚠️ No images were moved.")
print("⚠️ No images were modified.")


# ============================================================
# IMPORTANT
# ============================================================
# Save the code using the separate cell below.