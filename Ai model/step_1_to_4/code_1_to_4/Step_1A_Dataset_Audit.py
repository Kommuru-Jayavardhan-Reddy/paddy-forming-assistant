# ============================================================
# STEP 1A — DATASET STRUCTURE & CLASS DISTRIBUTION AUDIT
#             + DRIVE OUTPUT BACKUP
# ============================================================

# ------------------------------------------------------------
# 0. MOUNT GOOGLE DRIVE
# ------------------------------------------------------------

from google.colab import drive
drive.mount('/content/drive')

from pathlib import Path
import pandas as pd


# ============================================================
# 1. DATASET PATH
# ============================================================

DATASET_DIR = Path(
    "/content/drive/MyDrive/final year project/Dataset"
)

RESULTS_DIR = Path(
    "/content/drive/MyDrive/final year project/results"
)

# Create results folder automatically
RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

print("=" * 70)
print("STEP 1A — PADDY DATASET AUDIT")
print("=" * 70)

print("\nDataset Path:")
print(DATASET_DIR)

print("\nResults Path:")
print(RESULTS_DIR)


# ============================================================
# 2. CHECK DATASET
# ============================================================

if not DATASET_DIR.exists():
    raise FileNotFoundError(
        f"\n❌ Dataset folder not found:\n{DATASET_DIR}"
    )

print("\n✅ Dataset folder found")


# ============================================================
# 3. VALID IMAGE EXTENSIONS
# ============================================================

VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
    ".webp"
}


# ============================================================
# 4. FIND CLASS FOLDERS
# ============================================================

class_folders = sorted([
    folder
    for folder in DATASET_DIR.iterdir()
    if folder.is_dir()
])

print("\n" + "=" * 70)
print("CLASS FOLDERS")
print("=" * 70)

print(f"\nTotal class folders: {len(class_folders)}\n")

for i, folder in enumerate(class_folders, start=1):
    print(f"{i:2d}. {folder.name}")


# ============================================================
# 5. COUNT IMAGES IN EACH CLASS
# ============================================================

class_counts = []

for folder in class_folders:

    image_count = sum(
        1
        for file in folder.iterdir()
        if file.is_file()
        and file.suffix.lower() in VALID_EXTENSIONS
    )

    class_counts.append({
        "Class": folder.name,
        "Image_Count": image_count
    })


# ============================================================
# 6. CREATE DATAFRAME
# ============================================================

df = pd.DataFrame(class_counts)

df = df.sort_values(
    by="Image_Count",
    ascending=False
).reset_index(drop=True)


# ============================================================
# 7. DISPLAY CLASS DISTRIBUTION
# ============================================================

print("\n" + "=" * 70)
print("CLASS DISTRIBUTION")
print("=" * 70)

display(df)


# ============================================================
# 8. DATASET SUMMARY
# ============================================================

total_images = int(df["Image_Count"].sum())
number_of_classes = len(df)

print("\n" + "=" * 70)
print("DATASET SUMMARY")
print("=" * 70)

print(f"\nNumber of Classes : {number_of_classes}")
print(f"Total Images     : {total_images:,}")


# ============================================================
# 9. LARGEST & SMALLEST CLASS
# ============================================================

largest = df.loc[df["Image_Count"].idxmax()]
smallest = df.loc[df["Image_Count"].idxmin()]

print("\nLargest Class:")
print(
    f"  {largest['Class']} → "
    f"{largest['Image_Count']:,} images"
)

print("\nSmallest Class:")
print(
    f"  {smallest['Class']} → "
    f"{smallest['Image_Count']:,} images"
)


# ============================================================
# 10. CLASS IMBALANCE RATIO
# ============================================================

if smallest["Image_Count"] > 0:

    imbalance_ratio = (
        largest["Image_Count"] /
        smallest["Image_Count"]
    )

    print(
        f"\nClass Imbalance Ratio : "
        f"{imbalance_ratio:.2f}"
    )

else:

    print("\n⚠️ A class contains zero images.")


# ============================================================
# 11. EMPTY CLASS CHECK
# ============================================================

empty_classes = df[
    df["Image_Count"] == 0
]

print("\n" + "=" * 70)
print("EMPTY CLASS CHECK")
print("=" * 70)

if empty_classes.empty:

    print("\n✅ No empty class folders.")

else:

    print("\n⚠️ Empty classes:")

    for cls in empty_classes["Class"]:
        print(" -", cls)


# ============================================================
# 12. SAVE CSV REPORT TO GOOGLE DRIVE
# ============================================================

csv_path = (
    RESULTS_DIR /
    "Step_1A_Class_Distribution.csv"
)

df.to_csv(
    csv_path,
    index=False
)

print("\n" + "=" * 70)
print("CSV REPORT SAVED")
print("=" * 70)

print(f"\n✅ {csv_path}")


# ============================================================
# 13. SAVE COMPLETE TEXT SUMMARY TO GOOGLE DRIVE
# ============================================================

txt_path = (
    RESULTS_DIR /
    "Step_1A_Dataset_Audit_Report.txt"
)

with open(txt_path, "w", encoding="utf-8") as f:

    f.write("=" * 70 + "\n")
    f.write("STEP 1A — PADDY DATASET AUDIT REPORT\n")
    f.write("=" * 70 + "\n\n")

    f.write(f"Dataset Path: {DATASET_DIR}\n")
    f.write(f"Number of Classes: {number_of_classes}\n")
    f.write(f"Total Images: {total_images:,}\n\n")

    f.write("=" * 70 + "\n")
    f.write("CLASS DISTRIBUTION\n")
    f.write("=" * 70 + "\n\n")

    f.write(
        df.to_string(index=False)
    )

    f.write("\n\n" + "=" * 70 + "\n")
    f.write("LARGEST CLASS\n")
    f.write("=" * 70 + "\n")

    f.write(
        f"{largest['Class']} → "
        f"{largest['Image_Count']:,} images\n"
    )

    f.write("\n" + "=" * 70 + "\n")
    f.write("SMALLEST CLASS\n")
    f.write("=" * 70 + "\n")

    f.write(
        f"{smallest['Class']} → "
        f"{smallest['Image_Count']:,} images\n"
    )

    f.write("\n" + "=" * 70 + "\n")
    f.write("CLASS IMBALANCE RATIO\n")
    f.write("=" * 70 + "\n")

    if smallest["Image_Count"] > 0:
        f.write(
            f"{imbalance_ratio:.2f}\n"
        )
    else:
        f.write("Undefined — zero-image class exists.\n")

    f.write("\n" + "=" * 70 + "\n")
    f.write("EMPTY CLASS CHECK\n")
    f.write("=" * 70 + "\n")

    if empty_classes.empty:
        f.write("No empty class folders.\n")
    else:
        for cls in empty_classes["Class"]:
            f.write(f"{cls}\n")


print("\n" + "=" * 70)
print("TEXT REPORT SAVED")
print("=" * 70)

print(f"\n✅ {txt_path}")


# ============================================================
# 14. FINAL STATUS
# ============================================================

print("\n" + "=" * 70)
print("STEP 1A COMPLETED SUCCESSFULLY")
print("=" * 70)

print("\n✅ Dataset checked")
print("✅ Class folders counted")
print("✅ Images counted")
print("✅ Class imbalance calculated")
print("✅ Empty classes checked")
print("✅ CSV report saved to Drive")
print("✅ Text audit report saved to Drive")

print("\n⚠️ No images were deleted.")
print("⚠️ No images were moved.")
print("⚠️ No images were modified.")

print("\n📁 Drive output folder:")
print(RESULTS_DIR)