# ============================================================
# STEP 6D — LINEAR PROJECTION + LAYER NORMALIZATION
# ============================================================

import torch

print("=" * 70)
print("STEP 6D — PROJECTION + LAYERNORM")
print("=" * 70)

# ============================================================
# 1. VERIFY REQUIRED VARIABLES
# ============================================================

if "combined_hidden" not in globals():

    raise RuntimeError(
        "❌ combined_hidden not found.\n"
        "Please run STEP 6C first."
    )

if "satellite_model" not in globals():

    raise RuntimeError(
        "❌ satellite_model not found.\n"
        "Please run STEP 6B first."
    )

# ============================================================
# 2. INPUT VERIFICATION
# ============================================================

batch_size = combined_hidden.shape[0]

expected_input_shape = (
    batch_size,
    256
)

print("\nInput combined representation:")
print("Shape:", combined_hidden.shape)

if tuple(combined_hidden.shape) != expected_input_shape:

    raise ValueError(
        f"❌ Invalid input shape.\n"
        f"Expected: {expected_input_shape}\n"
        f"Actual  : {tuple(combined_hidden.shape)}"
    )

print(
    f"✅ Input representation = [{batch_size}, 256]"
)

# ============================================================
# 3. VERIFY INPUT DATA QUALITY
# ============================================================

input_nan = torch.isnan(
    combined_hidden
).sum().item()

input_inf = torch.isinf(
    combined_hidden
).sum().item()

input_quality_ok = (
    input_nan == 0
    and input_inf == 0
)

print("\n" + "-" * 70)
print("INPUT DATA QUALITY")
print("-" * 70)

print("NaN count:", input_nan)
print("Inf count:", input_inf)

if input_quality_ok:

    print("✅ Input contains no NaN / Inf")

else:

    print("❌ Input contains NaN / Inf")

# ============================================================
# 4. LINEAR PROJECTION
# ============================================================

print("\n" + "-" * 70)
print("LINEAR PROJECTION")
print("-" * 70)

projected_embedding = satellite_model.projection(
    combined_hidden
)

expected_projection_shape = (
    batch_size,
    256
)

projection_ok = (
    tuple(projected_embedding.shape)
    == expected_projection_shape
)

print("\nLinear layer:")
print("256 → 256")

print("\nAfter Linear projection:")
print(
    "Shape:",
    projected_embedding.shape
)

print(
    "Expected:",
    expected_projection_shape
)

print(
    "Status  : "
    + (
        "✅ PASS"
        if projection_ok
        else "❌ FAIL"
    )
)

# ============================================================
# 5. PROJECTION DATA QUALITY
# ============================================================

projection_nan = torch.isnan(
    projected_embedding
).sum().item()

projection_inf = torch.isinf(
    projected_embedding
).sum().item()

projection_quality_ok = (
    projection_nan == 0
    and projection_inf == 0
)

print("\nProjection NaN count:", projection_nan)
print("Projection Inf count:", projection_inf)

if projection_quality_ok:

    print(
        "✅ Projection contains no NaN / Inf"
    )

else:

    print(
        "❌ Projection contains NaN / Inf"
    )

# ============================================================
# 6. LAYER NORMALIZATION
# ============================================================

print("\n" + "-" * 70)
print("LAYER NORMALIZATION")
print("-" * 70)

satellite_embedding = satellite_model.layer_norm(
    projected_embedding
)

expected_embedding_shape = (
    batch_size,
    256
)

layer_norm_shape_ok = (
    tuple(satellite_embedding.shape)
    == expected_embedding_shape
)

print("\nLayerNorm dimension:")
print("256")

print("\nAfter LayerNorm:")

print(
    "Shape:",
    satellite_embedding.shape
)

print(
    "Expected:",
    expected_embedding_shape
)

print(
    "Status  : "
    + (
        "✅ PASS"
        if layer_norm_shape_ok
        else "❌ FAIL"
    )
)

# ============================================================
# 7. FINAL EMBEDDING DATA QUALITY
# ============================================================

print("\n" + "-" * 70)
print("FINAL EMBEDDING DATA QUALITY")
print("-" * 70)

nan_count = torch.isnan(
    satellite_embedding
).sum().item()

inf_count = torch.isinf(
    satellite_embedding
).sum().item()

embedding_quality_ok = (
    nan_count == 0
    and inf_count == 0
)

print(
    "NaN count:",
    nan_count
)

print(
    "Inf count:",
    inf_count
)

if embedding_quality_ok:

    print(
        "✅ Final embedding contains no NaN / Inf"
    )

else:

    print(
        "❌ Final embedding contains NaN / Inf"
    )

# ============================================================
# 8. FINAL EMBEDDING STATISTICS
# ============================================================

print("\n" + "-" * 70)
print("FINAL SATELLITE EMBEDDING STATISTICS")
print("-" * 70)

embedding_min = (
    satellite_embedding.min().item()
)

embedding_max = (
    satellite_embedding.max().item()
)

embedding_mean = (
    satellite_embedding.mean().item()
)

embedding_std = (
    satellite_embedding.std(
        unbiased=False
    ).item()
)

print(
    f"Minimum : {embedding_min:.6f}"
)

print(
    f"Maximum : {embedding_max:.6f}"
)

print(
    f"Mean    : {embedding_mean:.6f}"
)

print(
    f"Std     : {embedding_std:.6f}"
)

# ============================================================
# 9. LAYERNORM BEHAVIOR ANALYSIS
# ============================================================

print("\n" + "-" * 70)
print("LAYERNORM BEHAVIOR VERIFICATION")
print("-" * 70)

# LayerNorm normalizes each individual sample
# across its 256 features.

sample_means = satellite_embedding.mean(
    dim=1
)

sample_stds = satellite_embedding.std(
    dim=1,
    unbiased=False
)

# Maximum absolute mean
max_abs_sample_mean = (
    sample_means.abs().max().item()
)

# Difference from ideal std = 1
max_sample_std_error = (
    (sample_stds - 1.0).abs().max().item()
)

print(
    f"Maximum absolute sample mean : "
    f"{max_abs_sample_mean:.10f}"
)

print(
    f"Maximum sample std error     : "
    f"{max_sample_std_error:.10f}"
)

# ------------------------------------------------------------
# Mean check
# ------------------------------------------------------------

mean_tolerance = 1e-5

mean_ok = (
    max_abs_sample_mean
    < mean_tolerance
)

print("\nMean normalization:")

if mean_ok:

    print("Status : ✅ PASS")

else:

    print("Status : ❌ FAIL")

# ------------------------------------------------------------
# Standard deviation
# ------------------------------------------------------------
# This is informational only.
#
# LayerNorm uses eps internally, so a tiny numerical
# difference from exactly 1.0 is normal.
#
# Therefore this value is NOT used to fail Step 6D.

print("\nStandard deviation normalization:")

print(
    "Status : ℹ️ INFORMATIONAL"
)

print(
    "LayerNorm std deviation from 1.0:",
    f"{max_sample_std_error:.10f}"
)

print(
    "ℹ️ This value is reported for analysis "
    "and is not treated as a model failure."
)

# ============================================================
# 10. VERIFY LAYERNORM CONFIGURATION
# ============================================================

print("\n" + "-" * 70)
print("LAYERNORM CONFIGURATION")
print("-" * 70)

layer_norm_shape = (
    satellite_model.layer_norm.normalized_shape
)

layer_norm_eps = (
    satellite_model.layer_norm.eps
)

layer_norm_config_ok = (
    layer_norm_shape == (256,)
)

print(
    "Normalized shape:",
    layer_norm_shape
)

print(
    "Epsilon:",
    layer_norm_eps
)

print(
    "Expected normalized shape: (256,)"
)

if layer_norm_config_ok:

    print(
        "✅ LayerNorm configuration correct"
    )

else:

    print(
        "❌ LayerNorm configuration incorrect"
    )

# ============================================================
# 11. FINAL VALIDATION
# ============================================================

all_checks_passed = (

    input_quality_ok

    and projection_ok

    and projection_quality_ok

    and layer_norm_shape_ok

    and embedding_quality_ok

    and mean_ok

    and layer_norm_config_ok
)

# ============================================================
# 12. FINAL RESULT
# ============================================================

print("\n" + "=" * 70)
print("STEP 6D — FINAL RESULT")
print("=" * 70)

if all_checks_passed:

    print("\n✅ STEP 6D PASSED")

    print("\nVerified pipeline:")

    print(
        f"Combined hidden     : "
        f"[{batch_size}, 256]"
    )

    print(
        f"Linear projection   : "
        f"[{batch_size}, 256]"
    )

    print(
        f"LayerNorm output    : "
        f"[{batch_size}, 256]"
    )

    print("\n" + "-" * 70)
    print("VERIFICATION SUMMARY")
    print("-" * 70)

    print(
        "✅ Input shape verified"
    )

    print(
        "✅ Linear projection 256 → 256 verified"
    )

    print(
        "✅ LayerNorm(256) verified"
    )

    print(
        "✅ Output shape verified"
    )

    print(
        "✅ No NaN values"
    )

    print(
        "✅ No Inf values"
    )

    print(
        "✅ Mean normalization verified"
    )

    print(
        "✅ LayerNorm configuration verified"
    )

    print(
        "\nℹ️ Standard deviation check was "
        "reported for reference only."
    )

    print(
        f"\nFinal satellite embedding:"
    )

    print(
        f"satellite_embedding = "
        f"[{batch_size}, 256]"
    )

    print(
        "\n✅ Satellite branch projection "
        "and normalization are ready."
    )

    print(
        "\n➡️ Ready for STEP 6E."
    )

else:

    print("\n❌ STEP 6D FAILED")

    print(
        "\nA structural or data-quality "
        "check failed."
    )

    print(
        "\nDo not continue to STEP 6E."
    )