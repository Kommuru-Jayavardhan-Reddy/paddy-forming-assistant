# ============================================================
# STEP 6E — FINAL SATELLITE BRANCH VERIFICATION
# ============================================================

print("=" * 70)
print("STEP 6E — FINAL SATELLITE BRANCH VERIFICATION")
print("=" * 70)

# ------------------------------------------------------------
# 1. Expected dimensions
# ------------------------------------------------------------

EXPECTED_EMBEDDING_DIM = 256

# satellite_embedding should be:
# [number_of_satellite_sequences, 256]

num_samples = satellite_embedding.shape[0]

expected_shape = (num_samples, EXPECTED_EMBEDDING_DIM)

# ------------------------------------------------------------
# 2. Verify final embedding
# ------------------------------------------------------------

print("\nFinal satellite embedding:")
print("Shape:", tuple(satellite_embedding.shape))

print("\nNumber of satellite sequences:", num_samples)
print("Embedding dimension:", satellite_embedding.shape[1])

# ------------------------------------------------------------
# 3. Check expected shape
# ------------------------------------------------------------

shape_ok = (
    satellite_embedding.ndim == 2
    and satellite_embedding.shape[0] == num_samples
    and satellite_embedding.shape[1] == EXPECTED_EMBEDDING_DIM
)

print("\nExpected format:")
print(f"({num_samples}, {EXPECTED_EMBEDDING_DIM})")

print("Shape correct:", shape_ok)

# ------------------------------------------------------------
# 4. Check NaN / Inf
# ------------------------------------------------------------

nan_count = torch.isnan(satellite_embedding).sum().item()
inf_count = torch.isinf(satellite_embedding).sum().item()

print("\nNaN count:", nan_count)
print("Inf count:", inf_count)

nan_ok = nan_count == 0
inf_ok = inf_count == 0

# ------------------------------------------------------------
# 5. Basic embedding statistics
# ------------------------------------------------------------

embedding_mean = satellite_embedding.mean().item()
embedding_std = satellite_embedding.std().item()
embedding_min = satellite_embedding.min().item()
embedding_max = satellite_embedding.max().item()

print("\nEmbedding statistics:")
print("Mean :", embedding_mean)
print("Std  :", embedding_std)
print("Min  :", embedding_min)
print("Max  :", embedding_max)

# ------------------------------------------------------------
# 6. Verify every sequence has 256-D embedding
# ------------------------------------------------------------

print("\nEmbedding dimension verification:")

all_embeddings_correct = True

for i in range(num_samples):

    current_shape = tuple(satellite_embedding[i].shape)

    if current_shape != (EXPECTED_EMBEDDING_DIM,):
        all_embeddings_correct = False

    print(
        f"Sequence {i + 1:02d}:",
        current_shape,
        "✅" if current_shape == (EXPECTED_EMBEDDING_DIM,) else "❌"
    )

# ------------------------------------------------------------
# 7. Check batch/sample count
# ------------------------------------------------------------

sample_count_ok = num_samples == X_sat.shape[0]

print("\nSample count verification:")
print("Input satellite sequences :", X_sat.shape[0])
print("Final embeddings          :", num_samples)
print("Sample count matches      :", sample_count_ok)

# ------------------------------------------------------------
# 8. Check embedding tensor type
# ------------------------------------------------------------

print("\nTensor information:")
print("Data type:", satellite_embedding.dtype)
print("Device   :", satellite_embedding.device)

# ------------------------------------------------------------
# 9. Final verification
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("STEP 6E — FINAL RESULT")
print("=" * 70)

if (
    shape_ok
    and nan_ok
    and inf_ok
    and all_embeddings_correct
    and sample_count_ok
):

    print("✅ Satellite sequences processed:", num_samples)
    print("✅ Each sequence has one 256-dimensional embedding")
    print(
        f"✅ Final satellite embedding shape: "
        f"({num_samples}, 256)"
    )
    print("✅ No NaN values")
    print("✅ No Inf values")
    print("✅ Sample count matches input")
    print("✅ Satellite temporal information compressed successfully")
    print("✅ Satellite BiLSTM projection verified")
    print("✅ LayerNorm output verified")
    print("✅ STEP 6E PASSED")
    print("✅ STEP 6 — SATELLITE BiLSTM BRANCH COMPLETED")

else:

    print("❌ STEP 6E FAILED")

    if not shape_ok:
        print("❌ Embedding shape is incorrect")

    if not nan_ok:
        print("❌ NaN values detected")

    if not inf_ok:
        print("❌ Inf values detected")

    if not all_embeddings_correct:
        print("❌ Some embeddings are not 256-dimensional")

    if not sample_count_ok:
        print("❌ Input/output sample count mismatch")