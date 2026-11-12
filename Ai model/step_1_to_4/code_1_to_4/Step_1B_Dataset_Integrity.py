# ============================================================
# STEP 1B — DATASET INTEGRITY & DUPLICATE AUDIT
#             + DRIVE CODE & REPORT BACKUP
# ============================================================

# ------------------------------------------------------------
# 0. MOUNT GOOGLE DRIVE
# ------------------------------------------------------------

from google.colab import drive
drive.mount('/content/drive')


# ------------------------------------------------------------
# 1. IMPORT LIBRARIES
# ------------------------------------------------------------

from pathlib import Path
from collections import defaultdict
import hashlib
import pandas as pd
from PIL import Image


# ============================================================
# 2. PROJECT PATHS
# ============================================================

PROJECT_DIR = Path(
    "/content/drive/MyDrive/final year project"
)

DATASET_DIR = PROJECT_DIR / "Dataset"
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
# 3. SETTINGS
# ============================================================

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}


# ============================================================
# 4. HEADER
# ============================================================

print("=" * 75)
print("STEP 1B — DATASET INTEGRITY & DUPLICATE AUDIT")
print("=" * 75)

print("\nDataset Path:")
print(DATASET_DIR)

print("\nResults Path:")
print(RESULTS_DIR)

print("\nCode Path:")
print(CODE_DIR)


# ============================================================
# 5. DATASET CHECK
# ============================================================

if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"\n❌ Dataset folder not found:\n{DATASET_DIR}"
    )

print("\n✅ Dataset folder found")


# ============================================================
# 6. FIND CLASS FOLDERS
# ============================================================

class_folders = sorted([
    folder
    for folder in DATASET_DIR.iterdir()
    if folder.is_dir()
])

print("\n" + "=" * 75)
print("CLASS FOLDERS")
print("=" * 75)

print(f"\nTotal Classes: {len(class_folders)}\n")

for i, folder in enumerate(class_folders, 1):
    print(f"{i:2d}. {folder.name}")


# ============================================================
# 7. COLLECT ALL FILES
# ============================================================

all_files = []

for class_folder in class_folders:

    for file in class_folder.iterdir():

        if file.is_file():
            all_files.append({
                "path": file,
                "class": class_folder.name
            })

print("\n" + "=" * 75)
print("FILE COLLECTION")
print("=" * 75)

print(f"\nTotal files found: {len(all_files):,}")


# ============================================================
# 8. CHECK VALID IMAGE / NON-IMAGE FILES
# ============================================================

valid_images = []
non_image_files = []
corrupt_images = []

print("\n" + "=" * 75)
print("IMAGE VALIDATION")
print("=" * 75)

for item in all_files:

    file_path = item["path"]
    class_name = item["class"]

    if file_path.suffix.lower() not in VALID_EXTENSIONS:

        non_image_files.append({
            "Class": class_name,
            "File": str(file_path)
        })

        continue

    try:

        with Image.open(file_path) as img:

            img.verify()

        valid_images.append({
            "path": file_path,
            "class": class_name
        })

    except Exception as e:

        corrupt_images.append({
            "Class": class_name,
            "File": str(file_path),
            "Error": str(e)
        })


print(f"\n✅ Valid images      : {len(valid_images):,}")
print(f"⚠️ Corrupt images   : {len(corrupt_images):,}")
print(f"⚠️ Non-image files  : {len(non_image_files):,}")


# ============================================================
# 9. IMAGE DIMENSION CHECK
# ============================================================

dimension_records = []

print("\n" + "=" * 75)
print("IMAGE DIMENSION CHECK")
print("=" * 75)

for item in valid_images:

    file_path = item["path"]
    class_name = item["class"]

    try:

        with Image.open(file_path) as img:

            width, height = img.size
            mode = img.mode

        dimension_records.append({
            "Class": class_name,
            "File": str(file_path),
            "Width": width,
            "Height": height,
            "Mode": mode
        })

    except Exception:
        pass


dimension_df = pd.DataFrame(
    dimension_records
)

if not dimension_df.empty:

    unique_dimensions = (
        dimension_df[
            ["Width", "Height"]
        ]
        .drop_duplicates()
        .sort_values(
            ["Width", "Height"]
        )
        .reset_index(drop=True)
    )

    print(
        f"\nUnique image dimensions: "
        f"{len(unique_dimensions)}"
    )

    print("\nMost common dimensions:")

    dimension_counts = (
        dimension_df
        .groupby(
            ["Width", "Height"]
        )
        .size()
        .reset_index(
            name="Image_Count"
        )
        .sort_values(
            "Image_Count",
            ascending=False
        )
        .head(10)
    )

    display(dimension_counts)

else:

    unique_dimensions = pd.DataFrame()


# ============================================================
# 10. SHA-256 HASH DUPLICATE CHECK
# ============================================================

print("\n" + "=" * 75)
print("SHA-256 DUPLICATE CHECK")
print("=" * 75)

hash_groups = defaultdict(list)

for index, item in enumerate(valid_images, 1):

    file_path = item["path"]

    try:

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

        hash_groups[file_hash].append(item)

    except Exception as e:

        corrupt_images.append({
            "Class": item["class"],
            "File": str(file_path),
            "Error": f"Hash error: {e}"
        })


# ============================================================
# 11. FIND DUPLICATE GROUPS
# ============================================================

duplicate_groups = {
    file_hash: files
    for file_hash, files in hash_groups.items()
    if len(files) > 1
}

duplicate_file_count = sum(
    len(files)
    for files in duplicate_groups.values()
)

duplicate_group_count = len(
    duplicate_groups
)

print(
    f"\nDuplicate groups : "
    f"{duplicate_group_count:,}"
)

print(
    f"Duplicate files  : "
    f"{duplicate_file_count:,}"
)


# ============================================================
# 12. WITHIN-CLASS VS CROSS-CLASS DUPLICATES
# ============================================================

within_class_groups = []
cross_class_groups = []

duplicate_records = []

for file_hash, files in duplicate_groups.items():

    classes = sorted(
        set(
            item["class"]
            for item in files
        )
    )

    if len(classes) == 1:

        duplicate_type = "Within-Class"

        within_class_groups.append({
            "SHA256": file_hash,
            "Class": classes[0],
            "File_Count": len(files)
        })

    else:

        duplicate_type = "Cross-Class"

        cross_class_groups.append({
            "SHA256": file_hash,
            "Classes": " | ".join(classes),
            "File_Count": len(files)
        })

    for item in files:

        duplicate_records.append({
            "SHA256": file_hash,
            "Class": item["class"],
            "File": str(item["path"]),
            "Duplicate_Type": duplicate_type
        })


print("\n" + "=" * 75)
print("DUPLICATE CLASSIFICATION")
print("=" * 75)

print(
    f"\nWithin-class duplicate groups : "
    f"{len(within_class_groups):,}"
)

print(
    f"Cross-class duplicate groups  : "
    f"{len(cross_class_groups):,}"
)


# ============================================================
# 13. CLASS DISTRIBUTION
# ============================================================

class_counts = []

for class_folder in class_folders:

    count = sum(
        1
        for item in valid_images
        if item["class"] == class_folder.name
    )

    class_counts.append({
        "Class": class_folder.name,
        "Valid_Image_Count": count
    })


class_df = pd.DataFrame(
    class_counts
).sort_values(
    "Valid_Image_Count",
    ascending=False
).reset_index(drop=True)


print("\n" + "=" * 75)
print("VALID IMAGE CLASS DISTRIBUTION")
print("=" * 75)

display(class_df)


# ============================================================
# 14. IMBALANCE RATIO
# ============================================================

largest = class_df.iloc[0]
smallest = class_df.iloc[-1]

if smallest["Valid_Image_Count"] > 0:

    imbalance_ratio = (
        largest["Valid_Image_Count"]
        /
        smallest["Valid_Image_Count"]
    )

else:

    imbalance_ratio = None


print("\nLargest Class:")
print(
    f"{largest['Class']} → "
    f"{largest['Valid_Image_Count']:,}"
)

print("\nSmallest Class:")
print(
    f"{smallest['Class']} → "
    f"{smallest['Valid_Image_Count']:,}"
)

if imbalance_ratio is not None:

    print(
        f"\nClass Imbalance Ratio: "
        f"{imbalance_ratio:.2f}×"
    )


# ============================================================
# 15. SAVE CLASS REPORT
# ============================================================

class_report_path = (
    RESULTS_DIR /
    "Step_1B_Class_Integrity.csv"
)

class_df.to_csv(
    class_report_path,
    index=False
)


# ============================================================
# 16. SAVE DUPLICATE REPORT
# ============================================================

duplicate_report_path = (
    RESULTS_DIR /
    "Step_1B_Duplicate_Report.csv"
)

if duplicate_records:

    duplicate_df = pd.DataFrame(
        duplicate_records
    )

    duplicate_df.to_csv(
        duplicate_report_path,
        index=False
    )

else:

    pd.DataFrame(
        columns=[
            "SHA256",
            "Class",
            "File",
            "Duplicate_Type"
        ]
    ).to_csv(
        duplicate_report_path,
        index=False
    )


# ============================================================
# 17. SAVE CORRUPT FILE REPORT
# ============================================================

corrupt_report_path = (
    RESULTS_DIR /
    "Step_1B_Corrupt_Files.csv"
)

pd.DataFrame(
    corrupt_images
).to_csv(
    corrupt_report_path,
    index=False
)


# ============================================================
# 18. SAVE NON-IMAGE REPORT
# ============================================================

non_image_report_path = (
    RESULTS_DIR /
    "Step_1B_Non_Image_Files.csv"
)

pd.DataFrame(
    non_image_files
).to_csv(
    non_image_report_path,
    index=False
)


# ============================================================
# 19. SAVE DIMENSION REPORT
# ============================================================

dimension_report_path = (
    RESULTS_DIR /
    "Step_1B_Image_Dimensions.csv"
)

dimension_df.to_csv(
    dimension_report_path,
    index=False
)


# ============================================================
# 20. SAVE COMPLETE TEXT REPORT
# ============================================================

text_report_path = (
    RESULTS_DIR /
    "Step_1B_Dataset_Integrity_Report.txt"
)

with open(
    text_report_path,
    "w",
    encoding="utf-8"
) as f:

    f.write("=" * 75 + "\n")
    f.write(
        "STEP 1B — DATASET INTEGRITY & DUPLICATE AUDIT\n"
    )
    f.write("=" * 75 + "\n\n")

    f.write(
        f"Dataset Path: {DATASET_DIR}\n"
    )

    f.write(
        f"Total Classes: {len(class_folders)}\n"
    )

    f.write(
        f"Total Files: {len(all_files):,}\n"
    )

    f.write(
        f"Valid Images: {len(valid_images):,}\n"
    )

    f.write(
        f"Corrupt Images: {len(corrupt_images):,}\n"
    )

    f.write(
        f"Non-Image Files: {len(non_image_files):,}\n"
    )

    f.write(
        f"Duplicate Groups: {duplicate_group_count:,}\n"
    )

    f.write(
        f"Duplicate Files: {duplicate_file_count:,}\n"
    )

    f.write(
        f"Within-Class Duplicate Groups: "
        f"{len(within_class_groups):,}\n"
    )

    f.write(
        f"Cross-Class Duplicate Groups: "
        f"{len(cross_class_groups):,}\n"
    )

    if imbalance_ratio is not None:

        f.write(
            f"Class Imbalance Ratio: "
            f"{imbalance_ratio:.2f}x\n"
        )

    f.write("\n" + "=" * 75 + "\n")
    f.write("FINAL STATUS\n")
    f.write("=" * 75 + "\n")

    f.write(
        "\nNO IMAGES WERE DELETED.\n"
    )

    f.write(
        "NO IMAGES WERE MOVED.\n"
    )

    f.write(
        "NO IMAGES WERE MODIFIED.\n"
    )


# ============================================================
# 21. SAVE THIS CODE TO GOOGLE DRIVE
# ============================================================

code_path = (
    CODE_DIR /
    "Step_1B_Dataset_Integrity.py"
)

# IMPORTANT:
# This cell must be executed immediately after the
# main Step 1B cell.

if len(In) >= 2:

    step_1b_code = In[-2]

    with open(
        code_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(step_1b_code)

    print("\n" + "=" * 75)
    print("STEP 1B CODE BACKUP")
    print("=" * 75)

    print(
        f"\n✅ Code saved to:\n{code_path}"
    )


# ============================================================
# 22. FINAL STATUS
# ============================================================

print("\n" + "=" * 75)
print("STEP 1B COMPLETED")
print("=" * 75)

print("\n✅ Dataset integrity checked")
print("✅ Corrupt images checked")
print("✅ Non-image files checked")
print("✅ SHA-256 duplicates checked")
print("✅ Within-class duplicates checked")
print("✅ Cross-class duplicates checked")
print("✅ Image dimensions checked")
print("✅ Class imbalance checked")

print("\n📁 Reports saved in:")
print(RESULTS_DIR)

print("\n📁 Code saved in:")
print(CODE_DIR)

print("\n⚠️ NO IMAGES WERE DELETED.")
print("⚠️ NO IMAGES WERE MOVED.")
print("⚠️ NO IMAGES WERE MODIFIED.")