import torch
import torch.nn as nn

# ============================================================
# STEP_6B — BIDIRECTIONAL LSTM ARCHITECTURE
# ============================================================

class SatelliteBiLSTM(nn.Module):

    def __init__(self):
        super().__init__()

        # ----------------------------------------------------
        # 1. 2-Layer Bidirectional LSTM
        # ----------------------------------------------------

        self.lstm = nn.LSTM(
            input_size=3,          # NDVI, NDRE, GNDVI
            hidden_size=128,       # 128 per direction
            num_layers=2,
            batch_first=True,
            dropout=0.3,           # dropout between LSTM layers
            bidirectional=True
        )

        # ----------------------------------------------------
        # 2. Projection Layer
        # ----------------------------------------------------
        # Forward hidden state  = 128
        # Backward hidden state = 128
        # Total                  = 256

        self.projection = nn.Linear(
            256,
            256
        )

        # ----------------------------------------------------
        # 3. Layer Normalization
        # ----------------------------------------------------

        self.layer_norm = nn.LayerNorm(256)

    # ========================================================
    # FORWARD PASS
    # ========================================================

    def forward(self, x):

        # x shape:
        # [batch, sequence_length, 3]

        lstm_output, (hidden, cell) = self.lstm(x)

        # hidden shape:
        # [num_layers * num_directions, batch, hidden_size]
        #
        # [4, batch, 128]

        # ----------------------------------------------------
        # Final layer forward hidden state
        # ----------------------------------------------------

        forward_hidden = hidden[-2]

        # Shape:
        # [batch, 128]

        # ----------------------------------------------------
        # Final layer backward hidden state
        # ----------------------------------------------------

        backward_hidden = hidden[-1]

        # Shape:
        # [batch, 128]

        # ----------------------------------------------------
        # Concatenate forward + backward
        # ----------------------------------------------------

        satellite_embedding = torch.cat(
            [forward_hidden, backward_hidden],
            dim=1
        )

        # Shape:
        # [batch, 256]

        # ----------------------------------------------------
        # Linear projection
        # ----------------------------------------------------

        satellite_embedding = self.projection(
            satellite_embedding
        )

        # Shape:
        # [batch, 256]

        # ----------------------------------------------------
        # Layer normalization
        # ----------------------------------------------------

        satellite_embedding = self.layer_norm(
            satellite_embedding
        )

        # Final output:
        # [batch, 256]

        return satellite_embedding


# ============================================================
# CREATE MODEL
# ============================================================

satellite_model = SatelliteBiLSTM()

print("=" * 70)
print("STEP 6B — BiLSTM ARCHITECTURE")
print("=" * 70)

print("\nModel architecture:\n")
print(satellite_model)

# ============================================================
# MODEL PARAMETERS
# ============================================================

print("\n" + "-" * 70)
print("MODEL CONFIGURATION")
print("-" * 70)

print("Input features          : 3")
print("Sequence length         : 10")
print("LSTM layers             : 2")
print("Hidden units/direction  : 128")
print("Bidirectional           : True")
print("Dropout                 : 0.3")
print("Forward hidden          : 128")
print("Backward hidden         : 128")
print("Combined embedding     : 256")
print("Projection             : 256 → 256")
print("LayerNorm              : 256")

# ============================================================
# PARAMETER COUNT
# ============================================================

total_parameters = sum(
    p.numel()
    for p in satellite_model.parameters()
)

trainable_parameters = sum(
    p.numel()
    for p in satellite_model.parameters()
    if p.requires_grad
)

print("\n" + "-" * 70)
print("PARAMETER COUNT")
print("-" * 70)

print(
    f"Total parameters     : {total_parameters:,}"
)

print(
    f"Trainable parameters : {trainable_parameters:,}"
)

# ============================================================
# STEP 6B — ARCHITECTURE CHECK
# ============================================================

print("\n" + "-" * 70)
print("ARCHITECTURE VERIFICATION")
print("-" * 70)

checks = {
    "Input features = 3":
        satellite_model.lstm.input_size == 3,

    "Hidden size = 128":
        satellite_model.lstm.hidden_size == 128,

    "LSTM layers = 2":
        satellite_model.lstm.num_layers == 2,

    "Bidirectional = True":
        satellite_model.lstm.bidirectional is True,

    "Dropout = 0.3":
        abs(satellite_model.lstm.dropout - 0.3) < 1e-6,

    "Projection = 256 → 256":
        satellite_model.projection.in_features == 256
        and satellite_model.projection.out_features == 256,

    "LayerNorm = 256":
        satellite_model.layer_norm.normalized_shape == (256,)
}

all_architecture_checks = True

for check_name, result in checks.items():

    if result:

        print(f"✅ {check_name}")

    else:

        print(f"❌ {check_name}")
        all_architecture_checks = False

# ============================================================
# STEP 6B — TEST WITH ACTUAL SATELLITE INPUT
# ============================================================

print("\n" + "-" * 70)
print("FORWARD PASS VERIFICATION")
print("-" * 70)

# Use the X_sat loaded in Step 6A
# Expected:
# X_sat shape = [58, 10, 3]

X_tensor = torch.tensor(
    X_sat,
    dtype=torch.float32
)

print("\nInput tensor shape:")
print(X_tensor.shape)

# ------------------------------------------------------------
# Forward pass
# ------------------------------------------------------------

satellite_model.eval()

with torch.no_grad():

    satellite_embedding = satellite_model(
        X_tensor
    )

print("\nOutput embedding shape:")
print(satellite_embedding.shape)

# ============================================================
# OUTPUT SHAPE VERIFICATION
# ============================================================

expected_output_shape = (
    X_tensor.shape[0],
    256
)

actual_output_shape = tuple(
    satellite_embedding.shape
)

print("\nExpected output:")
print(expected_output_shape)

print("\nActual output:")
print(actual_output_shape)

output_shape_ok = (
    actual_output_shape == expected_output_shape
)

if output_shape_ok:

    print(
        "\n✅ Output shape verification PASSED"
    )

else:

    print(
        "\n❌ Output shape verification FAILED"
    )

# ============================================================
# EMBEDDING DATA QUALITY
# ============================================================

embedding_nan = torch.isnan(
    satellite_embedding
).sum().item()

embedding_inf = torch.isinf(
    satellite_embedding
).sum().item()

print("\n" + "-" * 70)
print("EMBEDDING DATA QUALITY")
print("-" * 70)

print(
    "NaN values :",
    embedding_nan
)

print(
    "Inf values :",
    embedding_inf
)

if embedding_nan == 0:

    print("✅ No NaN values")

else:

    print("❌ NaN values detected")

if embedding_inf == 0:

    print("✅ No Inf values")

else:

    print("❌ Inf values detected")

# ============================================================
# FINAL STEP 6B RESULT
# ============================================================

print("\n" + "=" * 70)
print("STEP 6B — FINAL RESULT")
print("=" * 70)

if (
    all_architecture_checks
    and output_shape_ok
    and embedding_nan == 0
    and embedding_inf == 0
):

    print("\n✅ STEP 6B PASSED")

    print("\nSatellite BiLSTM branch is correctly implemented.")

    print("\nInput:")
    print(
        f"  [batch={X_tensor.shape[0]}, "
        f"sequence_length={X_tensor.shape[1]}, "
        f"features={X_tensor.shape[2]}]"
    )

    print("\nOutput:")
    print(
        f"  [batch={satellite_embedding.shape[0]}, "
        f"embedding=256]"
    )

    print("\nReady for STEP 6C.")

else:

    print("\n❌ STEP 6B FAILED")

    print(
        "\nDo not continue until the failed checks are fixed."
    )