# ============================================================
# STEP_6C — BiLSTM FORWARD PASS & HIDDEN STATE VERIFICATION
# ============================================================

import torch

print("=" * 70)
print("STEP 6C — BiLSTM FORWARD PASS")
print("=" * 70)

# ============================================================
# 1. VERIFY REQUIRED VARIABLES
# ============================================================

if "X_sat" not in globals():

    raise RuntimeError(
        "❌ X_sat not found.\n"
        "Please run STEP 6A first."
    )

if "satellite_model" not in globals():

    raise RuntimeError(
        "❌ satellite_model not found.\n"
        "Please run STEP 6B first."
    )

# ============================================================
# 2. CONVERT NUMPY → PYTORCH TENSOR
# ============================================================

X_sat_tensor = torch.tensor(
    X_sat,
    dtype=torch.float32
)

print("\nInput tensor shape:")
print(X_sat_tensor.shape)

# ============================================================
# 3. EXTRACT ACTUAL DIMENSIONS
# ============================================================

batch_size = X_sat_tensor.shape[0]
sequence_length = X_sat_tensor.shape[1]
input_features = X_sat_tensor.shape[2]

print("\n" + "-" * 70)
print("INPUT DIMENSIONS")
print("-" * 70)

print("Batch size      :", batch_size)
print("Sequence length :", sequence_length)
print("Input features  :", input_features)

# ============================================================
# 4. VERIFY INPUT FORMAT
# ============================================================

if input_features != 3:

    raise ValueError(
        f"❌ Expected 3 input features, "
        f"but received {input_features}."
    )

if sequence_length != 10:

    raise ValueError(
        f"❌ Expected sequence length 10, "
        f"but received {sequence_length}."
    )

print("\n✅ Input format verified")
print(
    f"✅ Input = [{batch_size}, {sequence_length}, {input_features}]"
)

# ============================================================
# 5. EVALUATION MODE
# ============================================================

satellite_model.eval()

# ============================================================
# 6. BiLSTM FORWARD PASS
# ============================================================

with torch.no_grad():

    lstm_output, (hidden, cell) = satellite_model.lstm(
        X_sat_tensor
    )

# ============================================================
# 7. LSTM OUTPUT SHAPES
# ============================================================

print("\n" + "-" * 70)
print("LSTM OUTPUT SHAPES")
print("-" * 70)

print("LSTM output :", lstm_output.shape)
print("Hidden      :", hidden.shape)
print("Cell        :", cell.shape)

# ============================================================
# EXPECTED SHAPES
# ============================================================

expected_lstm_output = (
    batch_size,
    sequence_length,
    256
)

expected_hidden = (
    4,                  # 2 layers × 2 directions
    batch_size,
    128
)

expected_cell = (
    4,
    batch_size,
    128
)

print("\nExpected shapes:")

print(
    "LSTM output :",
    expected_lstm_output
)

print(
    "Hidden      :",
    expected_hidden
)

print(
    "Cell        :",
    expected_cell
)

# ============================================================
# 8. VERIFY LSTM OUTPUT
# ============================================================

lstm_output_ok = (
    tuple(lstm_output.shape)
    == expected_lstm_output
)

hidden_ok = (
    tuple(hidden.shape)
    == expected_hidden
)

cell_ok = (
    tuple(cell.shape)
    == expected_cell
)

print("\nShape verification:")

print(
    "LSTM output : "
    + ("✅ PASS" if lstm_output_ok else "❌ FAIL")
)

print(
    "Hidden      : "
    + ("✅ PASS" if hidden_ok else "❌ FAIL")
)

print(
    "Cell        : "
    + ("✅ PASS" if cell_ok else "❌ FAIL")
)

# ============================================================
# 9. EXTRACT FINAL LAYER FORWARD STATE
# ============================================================

# hidden structure:
#
# hidden[0] → Layer 1 Forward
# hidden[1] → Layer 1 Backward
# hidden[2] → Layer 2 Forward
# hidden[3] → Layer 2 Backward

forward_hidden = hidden[-2]

print("\n" + "-" * 70)
print("FINAL FORWARD HIDDEN STATE")
print("-" * 70)

print(
    "Forward hidden shape:",
    forward_hidden.shape
)

expected_forward_shape = (
    batch_size,
    128
)

forward_ok = (
    tuple(forward_hidden.shape)
    == expected_forward_shape
)

print(
    "Expected:",
    expected_forward_shape
)

print(
    "Status   : "
    + ("✅ PASS" if forward_ok else "❌ FAIL")
)

# ============================================================
# 10. EXTRACT FINAL LAYER BACKWARD STATE
# ============================================================

backward_hidden = hidden[-1]

print("\n" + "-" * 70)
print("FINAL BACKWARD HIDDEN STATE")
print("-" * 70)

print(
    "Backward hidden shape:",
    backward_hidden.shape
)

expected_backward_shape = (
    batch_size,
    128
)

backward_ok = (
    tuple(backward_hidden.shape)
    == expected_backward_shape
)

print(
    "Expected:",
    expected_backward_shape
)

print(
    "Status   : "
    + ("✅ PASS" if backward_ok else "❌ FAIL")
)

# ============================================================
# 11. CONCATENATE FORWARD + BACKWARD
# ============================================================

combined_hidden = torch.cat(
    [
        forward_hidden,
        backward_hidden
    ],
    dim=1
)

print("\n" + "-" * 70)
print("CONCATENATED REPRESENTATION")
print("-" * 70)

print(
    "Combined shape:",
    combined_hidden.shape
)

expected_combined_shape = (
    batch_size,
    256
)

combined_ok = (
    tuple(combined_hidden.shape)
    == expected_combined_shape
)

print(
    "Expected:",
    expected_combined_shape
)

print(
    "Status   : "
    + ("✅ PASS" if combined_ok else "❌ FAIL")
)

# ============================================================
# 12. CHECK FOR NaN / INF
# ============================================================

print("\n" + "-" * 70)
print("HIDDEN STATE DATA QUALITY")
print("-" * 70)

hidden_nan = torch.isnan(
    combined_hidden
).sum().item()

hidden_inf = torch.isinf(
    combined_hidden
).sum().item()

print(
    "NaN count:",
    hidden_nan
)

print(
    "Inf count:",
    hidden_inf
)

hidden_quality_ok = (
    hidden_nan == 0
    and hidden_inf == 0
)

if hidden_quality_ok:

    print("✅ No NaN / Inf in combined representation")

else:

    print("❌ NaN or Inf detected")

# ============================================================
# 13. BASIC EMBEDDING STATISTICS
# ============================================================

print("\n" + "-" * 70)
print("COMBINED HIDDEN STATE STATISTICS")
print("-" * 70)

print(
    f"Minimum : {combined_hidden.min().item():.6f}"
)

print(
    f"Maximum : {combined_hidden.max().item():.6f}"
)

print(
    f"Mean    : {combined_hidden.mean().item():.6f}"
)

print(
    f"Std     : {combined_hidden.std().item():.6f}"
)

# ============================================================
# 14. FINAL STEP 6C VALIDATION
# ============================================================

all_checks_passed = (
    lstm_output_ok
    and hidden_ok
    and cell_ok
    and forward_ok
    and backward_ok
    and combined_ok
    and hidden_quality_ok
)

print("\n" + "=" * 70)
print("STEP 6C — FINAL RESULT")
print("=" * 70)

if all_checks_passed:

    print("\n✅ STEP 6C PASSED")

    print("\nVerified architecture flow:")

    print(
        f"Input             : "
        f"[{batch_size}, {sequence_length}, {input_features}]"
    )

    print(
        f"LSTM output       : "
        f"[{batch_size}, {sequence_length}, 256]"
    )

    print(
        f"Forward hidden    : "
        f"[{batch_size}, 128]"
    )

    print(
        f"Backward hidden   : "
        f"[{batch_size}, 128]"
    )

    print(
        f"Combined           : "
        f"[{batch_size}, 256]"
    )

    print("\n✅ Forward and backward final states verified.")
    print("✅ 256-dimensional combined representation verified.")
    print("✅ No NaN / Inf detected.")

    print("\nReady for STEP 6D.")

else:

    print("\n❌ STEP 6C FAILED")

    print(
        "\nDo not continue to STEP 6D."
    )

    print(
        "Fix the failed shape or data-quality checks first."
    )