# =============================================================================
# STEP_7A — FIND EXISTING EFFICIENTNET-B4 PHASE-C CHECKPOINT
# =============================================================================

import os
from pathlib import Path

print("=" * 80)
print("STEP 7A.1 — SEARCHING FOR EXISTING EFFICIENTNET-B4 CHECKPOINT")
print("=" * 80)

# -------------------------------------------------------------------------
# 1. Google Drive check
# -------------------------------------------------------------------------

DRIVE_ROOT = "/content/drive/MyDrive"

if not os.path.exists(DRIVE_ROOT):
    print("\n❌ Google Drive is not mounted.")
    print("Please run:")
    print("from google.colab import drive")
    print("drive.mount('/content/drive')")
    raise SystemExit

print("\n✓ Google Drive is mounted.")


# -------------------------------------------------------------------------
# 2. Search for EfficientNet / Phase-C checkpoint files
# -------------------------------------------------------------------------

search_root = Path(DRIVE_ROOT)

keywords = [
    "efficientnet",
    "phasec",
    "phase_c",
    "phase-c",
]

checkpoint_extensions = {
    ".pth",
    ".pt",
    ".ckpt",
    ".bin"
}

matches = []

print("\nSearching Drive...")
print("-" * 80)

for root, dirs, files in os.walk(search_root):

    # Skip unnecessary hidden/system folders
    dirs[:] = [
        d for d in dirs
        if not d.startswith(".")
        and d not in ["node_modules", "__pycache__"]
    ]

    for file in files:

        file_lower = file.lower()
        ext = Path(file).suffix.lower()

        if ext not in checkpoint_extensions:
            continue

        if any(keyword in file_lower for keyword in keywords):

            full_path = os.path.join(root, file)

            try:
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            except:
                size_mb = -1

            matches.append(
                (full_path, size_mb)
            )


# -------------------------------------------------------------------------
# 3. Display results
# -------------------------------------------------------------------------

print("\n" + "=" * 80)
print("CHECKPOINT SEARCH RESULTS")
print("=" * 80)

if len(matches) == 0:

    print("\n❌ NO EfficientNet / Phase-C checkpoint found.")

else:

    print(f"\n✓ Checkpoint files found: {len(matches)}\n")

    for i, (path, size_mb) in enumerate(matches, 1):

        print(f"[{i}]")
        print(f"File : {path}")

        if size_mb >= 0:
            print(f"Size : {size_mb:.2f} MB")

        print("-" * 80)


# -------------------------------------------------------------------------
# 4. Identify likely Phase-C checkpoint
# -------------------------------------------------------------------------

print("\n" + "=" * 80)
print("LIKELY PHASE-C CHECKPOINTS")
print("=" * 80)

phase_c_matches = []

for path, size_mb in matches:

    name = os.path.basename(path).lower()

    if (
        "phasec" in name
        or "phase_c" in name
        or "phase-c" in name
    ):
        phase_c_matches.append((path, size_mb))


if len(phase_c_matches) == 0:

    print("\n⚠️ No filename explicitly contains Phase-C.")

    print("\nWe will NOT guess the checkpoint.")

else:

    print(
        f"\n✓ Phase-C-like checkpoint(s): "
        f"{len(phase_c_matches)}\n"
    )

    for i, (path, size_mb) in enumerate(phase_c_matches, 1):

        print(f"[{i}] {path}")
        print(f"    Size: {size_mb:.2f} MB")


# -------------------------------------------------------------------------
# 5. IMPORTANT — DO NOT LOAD / TRAIN MODEL YET
# -------------------------------------------------------------------------

print("\n" + "=" * 80)
print("CURRENT STATUS")
print("=" * 80)

print("""
Satellite branch:
    STEP 6
    ✓ COMPLETE
    ✓ 58 × 256 embeddings verified
    ✓ FIELD_01 → embedding[0]
    ✓ FIELD_58 → embedding[57]

Image branch:
    ✓ Existing EfficientNet-B4 model should be reused
    ⏳ Checkpoint location verification in progress

Multimodal training:
    ❌ NOT STARTED

IMPORTANT:
    Do not train anything in this step.
    Do not regenerate satellite embeddings.
    Do not modify GPS mapping.
""")

print("=" * 80)
print("STEP 7A CHECKPOINT SEARCH FINISHED")
print("=" * 80)