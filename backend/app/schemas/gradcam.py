"""
Paddy Farming Assistant - Grad-CAM Schemas (STEP 11D.5)
Defines Pydantic response models for visual explanation endpoints.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class GradCAMResponse(BaseModel):
    """
    Standard response payload for POST /explain/gradcam.
    Contains prediction details, target class explained, numerical statistics,
    and the visual overlay encoded as base64 data URI and saved file URL.
    """
    status: str = Field(default="success", description="Status of the Grad-CAM computation")
    predicted_class: str = Field(..., description="Top predicted paddy disease class by EfficientNet-B4")
    predicted_index: int = Field(..., description="Index of the top predicted disease class (0-12)")
    confidence: float = Field(..., description="Softmax confidence probability of the prediction [0.0 - 1.0]")
    target_class: str = Field(..., description="Disease class for which Grad-CAM was computed")
    target_index: int = Field(..., description="Class index explained by Grad-CAM (0-12)")
    target_layer: str = Field(
        default="features.8",
        description="Target convolutional stage in EfficientNet-B4 backbone (features[8])",
    )
    image_dimensions: Dict[str, int] = Field(
        ..., description="Original image spatial dimensions (width, height in pixels)"
    )
    heatmap_intensity_mean: float = Field(
        ..., description="Mean normalized heatmap intensity across original image pixels [0.0 - 1.0]"
    )
    heatmap_intensity_max: float = Field(
        ..., description="Peak normalized heatmap intensity [0.0 - 1.0]"
    )
    overlay_image: str = Field(
        ..., description="Base64 data URI of the generated Grad-CAM overlay (data:image/jpeg;base64,...)"
    )
    visualization_url: Optional[str] = Field(
        default=None, description="Relative URL to the saved visualization image on disk"
    )
    media_type: str = Field(default="image/jpeg", description="MIME media type of the overlay")
    device: str = Field(default="cpu", description="Hardware device utilized for inference and gradient backpropagation")
    limitations_note: str = Field(
        default=(
            "Grad-CAM is a visual explanation of neural network activation sensitivity, "
            "not proof of biological causation or definitive lesion pathology. "
            "Highlighted regions indicate receptive fields that increased the target class score, "
            "not verified histological boundaries."
        ),
        description="Scientific interpretation warning and limitations",
    )
