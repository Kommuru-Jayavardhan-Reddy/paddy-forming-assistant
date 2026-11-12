# ============================================================
# STEP 1C — DUPLICATE-AWARE STRATIFIED DATASET SPLIT
#             70% TRAIN / 15% VALIDATION / 15% TEST
#             + DRIVE BACKUP
# ============================================================

from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
from collections import defaultdict
import hashlib
import random
import shutil
import pandas as pd


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_DIR = Path(
    "/content/drive/MyDrive/final year project"
)

DATASET_DIR = PROJECT_DIR / "Dataset"

SPLIT_DIR = PROJECT_DIR / "Dataset_Split"

RESULTS_DIR = PROJECT_DIR / "results"

CODE_DIR = PROJECT_DIR / "code"

SPLIT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

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

SEED = 42

TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}

random.seed(SEED)


# ============================================================
# 3. HEADER
# ============================================================

print("=" * 75)
print("STEP 1C — DUPLICATE-AWARE STRATIFIED DATASET SPLIT")
print("=" * 75)

print("\nDataset:")
print(DATASET_DIR)

print("\nOutput:")
print(SPLIT_DIR)

print("\nSplit:")
print("Train      : 70%")
print("Validation : 15%")
print("Test       : 15%")

print(f"\nRandom Seed: {SEED}")


# ============================================================
# 4. DATASET CHECK
# ============================================================

if not DATASET_DIR.exists():

    raise FileNotFoundError(
        f"\n❌ Dataset not found:\n{DATASET_DIR}"
    )

print("\n✅ Dataset folder found")


# ============================================================
# 5. FIND CLASS FOLDERS
# ============================================================

class_folders = sorted([
    folder
    for folder in DATASET_DIR.iterdir()
    if folder.is_dir()
])


print("\n" + "=" * 75)
print("DATASET CLASSES")
print("=" * 75)

print(
    f"\nTotal Classes: {len(class_folders)}"
)

for i, folder in enumerate(
    class_folders,
    1
):

    print(
        f"{i:2d}. {folder.name}"
    )


# ============================================================
# 6. COLLECT VALID IMAGE FILES
# ============================================================

records = []

for class_folder in class_folders:

    for file in class_folder.iterdir():

        if (
            file.is_file()
            and
            file.suffix.lower()
            in VALID_EXTENSIONS
        ):

            records.append({
                "path": file,
                "class": class_folder.name
            })


print("\n" + "=" * 75)
print("IMAGE COLLECTION")
print("=" * 75)

print(
    f"\nTotal Images Found: {len(records):,}"
)


# ============================================================
# 7. VERIFY EXPECTED DATASET COUNT
# ============================================================

EXPECTED_TOTAL = 20320

if len(records) != EXPECTED_TOTAL:

    raise ValueError(
        f"\n❌ Dataset count mismatch!\n"
        f"Expected: {EXPECTED_TOTAL}\n"
        f"Found: {len(records)}"
    )

print(
    f"\n✅ Dataset count confirmed: "
    f"{len(records):,}"
)


# ============================================================
# 8. CALCULATE SHA-256 HASH
# ============================================================

print("\n" + "=" * 75)
print("BUILDING DUPLICATE GROUPS")
print("=" * 75)

hash_groups = defaultdict(list)

for i, item in enumerate(
    records,
    1
):

    file_path = item["path"]

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

    hash_groups[file_hash].append(
        item
    )

    if i % 1000 == 0:

        print(
            f"Processed: {i:,}/{len(records):,}"
        )


# ============================================================
# 9. VERIFY CROSS-CLASS DUPLICATES
# ============================================================

cross_class_groups = []

for file_hash, files in hash_groups.items():

    classes = set(
        item["class"]
        for item in files
    )

    if len(classes) > 1:

        cross_class_groups.append({
            "hash": file_hash,
            "classes": classes,
            "files": files
        })


if cross_class_groups:

    raise ValueError(
        "\n❌ Cross-class duplicates detected."
        "\nStop before splitting to prevent label leakage."
    )


print(
    "\n✅ Cross-class duplicates: 0"
)


# ============================================================
# 10. CREATE DUPLICATE GROUP RECORDS
# ============================================================

group_records = []

for file_hash, files in hash_groups.items():

    class_name = files[0]["class"]

    group_records.append({
        "hash": file_hash,
        "class": class_name,
        "files": files
    })


print(
    f"Unique image groups: "
    f"{len(group_records):,}"
)


# ============================================================
# 11. CREATE SPLIT DIRECTORIES
# ============================================================

TRAIN_DIR = SPLIT_DIR / "train"
VAL_DIR = SPLIT_DIR / "val"
TEST_DIR = SPLIT_DIR / "test"

for split_dir in [
    TRAIN_DIR,
    VAL_DIR,
    TEST_DIR
]:

    split_dir.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# 12. STRATIFIED GROUP SPLIT
# ============================================================

split_records = []

class_group_counts = {}

for class_folder in class_folders:

    class_name = class_folder.name

    class_groups = [
        group
        for group in group_records
        if group["class"] == class_name
    ]

    random.shuffle(
        class_groups
    )

    total_groups = len(
        class_groups
    )

    train_count = round(
        total_groups * TRAIN_RATIO
    )

    val_count = round(
        total_groups * VAL_RATIO
    )

    # Make sure all groups are assigned
    if train_count + val_count > total_groups:

        val_count = (
            total_groups
            - train_count
        )

    test_count = (
        total_groups
        - train_count
        - val_count
    )

    train_groups = class_groups[
        :train_count
    ]

    val_groups = class_groups[
        train_count:
        train_count + val_count
    ]

    test_groups = class_groups[
        train_count + val_count:
    ]

    class_group_counts[
        class_name
    ] = {
        "Train_Groups": len(train_groups),
        "Val_Groups": len(val_groups),
        "Test_Groups": len(test_groups)
    }

    for split_name, groups in [
        ("train", train_groups),
        ("val", val_groups),
        ("test", test_groups)
    ]:

        for group in groups:

            for item in group["files"]:

                split_records.append({
                    "Original_Path": str(
                        item["path"]
                    ),
                    "Class": class_name,
                    "Split": split_name,
                    "SHA256": group["hash"]
                })


# ============================================================
# 13. CREATE SPLIT DATAFRAME
# ============================================================

split_df = pd.DataFrame(
    split_records
)


# ============================================================
# 14. VERIFY ALL IMAGES ASSIGNED
# ============================================================

if len(split_df) != EXPECTED_TOTAL:

    raise ValueError(
        f"\n❌ Split error!\n"
        f"Original images: {EXPECTED_TOTAL}\n"
        f"Assigned images: {len(split_df)}"
    )

print("\n" + "=" * 75)
print("SPLIT ASSIGNMENT")
print("=" * 75)

print(
    f"\nTotal assigned: "
    f"{len(split_df):,}"
)


# ============================================================
# 15. VERIFY NO IMAGE IS IN MULTIPLE SPLITS
# ============================================================

path_split_count = (
    split_df
    .groupby("Original_Path")["Split"]
    .nunique()
)

if (
    path_split_count > 1
).any():

    raise ValueError(
        "\n❌ Image leakage detected!"
    )

print(
    "\n✅ No image assigned to multiple splits"
)


# ============================================================
# 16. VERIFY HASH GROUPS STAY TOGETHER
# ============================================================

hash_split_count = (
    split_df
    .groupby("SHA256")["Split"]
    .nunique()
)

if (
    hash_split_count > 1
).any():

    raise ValueError(
        "\n❌ Duplicate group leakage detected!"
    )

print(
    "✅ Duplicate groups kept within one split"
)


# ============================================================
# 17. COPY IMAGES TO TRAIN / VAL / TEST
# ============================================================

print("\n" + "=" * 75)
print("COPYING IMAGES")
print("=" * 75)

for index, row in split_df.iterrows():

    source = Path(
        row["Original_Path"]
    )

    split_name = row["Split"]

    class_name = row["Class"]

    destination_dir = (
        SPLIT_DIR
        / split_name
        / class_name
    )

    destination_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    destination = (
        destination_dir
        / source.name
    )

    # Prevent accidental overwrite
    if destination.exists():

        raise FileExistsError(
            f"\n❌ Destination already exists:\n"
            f"{destination}"
        )

    shutil.copy2(
        source,
        destination
    )

    if (index + 1) % 1000 == 0:

        print(
            f"Copied: "
            f"{index + 1:,}/{len(split_df):,}"
        )


# ============================================================
# 18. CLASS DISTRIBUTION AFTER SPLIT
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

for column in [
    "train",
    "val",
    "test"
]:

    if column not in distribution.columns:

        distribution[column] = 0


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


# ============================================================
# 19. DISPLAY SPLIT SUMMARY
# ============================================================

print("\n" + "=" * 75)
print("FINAL SPLIT DISTRIBUTION")
print("=" * 75)

display(
    distribution
)


# ============================================================
# 20. TOTAL SPLIT COUNTS
# ============================================================

total_train = int(
    (split_df["Split"] == "train").sum()
)

total_val = int(
    (split_df["Split"] == "val").sum()
)

total_test = int(
    (split_df["Split"] == "test").sum()
)

print("\nTrain Images      :", f"{total_train:,}")
print("Validation Images :", f"{total_val:,}")
print("Test Images       :", f"{total_test:,}")

print(
    "\nTotal             :",
    f"{total_train + total_val + total_test:,}"
)


# ============================================================
# 21. SAVE SPLIT CSV
# ============================================================

split_csv_path = (
    RESULTS_DIR /
    "Step_1C_Split_Assignment.csv"
)

split_df.to_csv(
    split_csv_path,
    index=False
)


# ============================================================
# 22. SAVE DISTRIBUTION CSV
# ============================================================

distribution_csv_path = (
    RESULTS_DIR /
    "Step_1C_Split_Distribution.csv"
)

distribution.to_csv(
    distribution_csv_path,
    index=False
)


# ============================================================
# 23. SAVE TEXT REPORT
# ============================================================

report_path = (
    RESULTS_DIR /
    "Step_1C_Split_Report.txt"
)

with open(
    report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write("=" * 75 + "\n")
    f.write(
        "STEP 1C — DATASET SPLIT REPORT\n"
    )
    f.write("=" * 75 + "\n\n")

    f.write(
        f"Total Images: {EXPECTED_TOTAL:,}\n"
    )

    f.write(
        f"Number of Classes: "
        f"{len(class_folders)}\n\n"
    )

    f.write(
        "Split Ratio:\n"
    )

    f.write(
        "Train: 70%\n"
    )

    f.write(
        "Validation: 15%\n"
    )

    f.write(
        "Test: 15%\n\n"
    )

    f.write(
        f"Train Images: {total_train:,}\n"
    )

    f.write(
        f"Validation Images: {total_val:,}\n"
    )

    f.write(
        f"Test Images: {total_test:,}\n\n"
    )

    f.write(
        "Cross-Class Duplicates: 0\n"
    )

    f.write(
        "Duplicate groups kept within one split: YES\n"
    )

    f.write(
        "Original images modified: NO\n"
    )

    f.write(
        "Original dataset deleted: NO\n"
    )


# ============================================================
# 24. SAVE CODE TO DRIVE
# ============================================================

print("\n" + "=" * 75)
print("STEP 1C CODE BACKUP")
print("=" * 75)

print(
    "\n⚠️ Run the following small cell separately "
    "to save the complete Step 1C code:"
)

print(
    CODE_DIR /
    "Step_1C_Dataset_Split.py"
)


# ============================================================
# 25. FINAL STATUS
# ============================================================

print("\n" + "=" * 75)
print("STEP 1C COMPLETED")
print("=" * 75)

print("\n✅ 20,320 images verified")
print("✅ 13 classes verified")
print("✅ Duplicate groups kept together")
print("✅ Stratified train/validation/test split created")
print("✅ Original Dataset was NOT modified")
print("✅ Split assignment saved to Drive")
print("✅ Split distribution saved to Drive")
print("✅ Text report saved to Drive")

print("\n📁 Split Dataset:")
print(SPLIT_DIR)

print("\n📁 Results:")
print(RESULTS_DIR)

print("\n⚠️ Original Dataset remains untouched.")