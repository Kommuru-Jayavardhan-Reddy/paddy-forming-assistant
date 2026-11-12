"""
Paddy Farming Assistant - SHAP Explanation Service (STEP 11D.6)
Provides feature-level explainability for the Multimodal Cross-Attention Model
using SHAP (SHapley Additive exPlanations) GradientExplainer over temporal satellite features
conditioned on the input leaf image embedding.
"""

import io
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
from PIL import Image

import torch
import torch.nn as nn
import shap

from app import config
from app.exceptions import ModelUnavailableError, FieldNotFoundError, SatelliteDataUnavailableError
from app.models.multimodal_model import MultimodalModelLoader, TemporalCrossAttentionModel
from app.services.multimodal_prediction import MultimodalPredictionService
from app.services.field_mapping import FieldMappingService

logger = logging.getLogger(__name__)


class SatelliteClassWrapper(nn.Module):
    """
    PyTorch wrapper module for GradientExplainer.
    Fixes the image embedding buffer and routes the variable satellite sequence
    through the TemporalCrossAttentionModel, returning a single target class logit.
    """

    def __init__(self, base_model: nn.Module, image_emb: torch.Tensor, target_class: int):
        super().__init__()
        self.base_model = base_model
        self.register_buffer("fixed_image", image_emb.detach().clone())
        self.target_class = int(target_class)

    def forward(self, sat_input: torch.Tensor) -> torch.Tensor:
        batch_size = sat_input.shape[0]
        img_batch = self.fixed_image.expand(batch_size, -1)
        logits, _ = self.base_model(img_batch, sat_input)
        return logits[:, self.target_class : self.target_class + 1]


class SHAPService:
    """
    Manages SHAP GradientExplainer lifecycle and execution for multimodal disease predictions.
    """

    _instance: Optional["SHAPService"] = None

    def __init__(self):
        self.device = config.DEVICE
        self.mm_service = MultimodalPredictionService()
        self.field_service = FieldMappingService.get_instance()
        self._raw_background: Optional[np.ndarray] = None
        self._normalized_background: Optional[torch.Tensor] = None
        self._background_indices: Optional[np.ndarray] = None
        self._is_initialized = False

    @classmethod
    def get_instance(cls) -> "SHAPService":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Loads the precomputed satellite background dataset and prepares normalized tensor.
        """
        if self._is_initialized:
            return

        bg_path: Path = config.SHAP_BACKGROUND_PATH
        idx_path: Path = config.SHAP_BACKGROUND_INDICES_PATH

        if not bg_path.exists():
            logger.error("SHAP background file not found at: %s", bg_path)
            raise FileNotFoundError(f"SHAP background dataset file does not exist: {bg_path}")

        try:
            self._raw_background = np.load(bg_path, allow_pickle=False)
            if self._raw_background.shape != (20, config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES):
                logger.warning(
                    "Unexpected SHAP background shape: %s; expected (20, %d, %d)",
                    self._raw_background.shape,
                    config.SATELLITE_TIMESTEPS,
                    config.NUM_SATELLITE_FEATURES,
                )

            if idx_path.exists():
                self._background_indices = np.load(idx_path, allow_pickle=False)

            # Retrieve checkpoint normalization stats
            meta = MultimodalModelLoader.get_metadata()
            sat_mean = torch.tensor(meta["satellite_mean"], dtype=torch.float32, device=self.device).view(1, 1, 3)
            sat_std = torch.tensor(meta["satellite_std"], dtype=torch.float32, device=self.device).view(1, 1, 3)

            bg_tensor = torch.tensor(self._raw_background, dtype=torch.float32, device=self.device)
            self._normalized_background = (bg_tensor - sat_mean) / sat_std

            self._is_initialized = True
            logger.info(
                "SHAPService initialized with %d background sequences (shape: %s).",
                len(self._raw_background),
                tuple(self._normalized_background.shape),
            )
        except Exception as exc:
            logger.error("Failed to initialize SHAP background: %s", exc)
            raise RuntimeError(f"Failed to initialize SHAP background dataset: {exc}") from exc

    def explain_multimodal(
        self,
        image_input: Union[bytes, io.BytesIO, Path, str, Image.Image],
        field_id: str,
        target_class: Optional[str] = None,
        target_index: Optional[int] = None,
        nsamples: Optional[int] = None,
        seed: Optional[int] = 42,
    ) -> Dict[str, Any]:
        """
        Computes SHAP GradientExplainer attributions for the multimodal model.
        Returns a structured dictionary matching SHAPExplanationResponse schema.
        """
        self._initialize()

        # Set reproducible seed if specified
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

        # 1. Load Multimodal Model & Metadata
        multimodal_model: TemporalCrossAttentionModel = MultimodalModelLoader.get_model()
        if multimodal_model is None:
            raise ModelUnavailableError("Multimodal cross-attention model is not loaded.")
        multimodal_meta = MultimodalModelLoader.get_metadata()
        class_names: List[str] = multimodal_meta["class_names"]

        # 2. Preprocess Leaf Image and Extract 1792-D Visual Embedding
        img_tensor = self.mm_service.preprocess_image(image_input).unsqueeze(0)
        img_embedding = self.mm_service.extract_image_embedding(img_tensor)

        # 3. Retrieve and Normalize Satellite Sequence for Requested Field
        sat_mean_np = np.array(multimodal_meta["satellite_mean"], dtype=np.float32)
        sat_std_np = np.array(multimodal_meta["satellite_std"], dtype=np.float32)
        sat_tensor, canonical_field_id = self.mm_service.prepare_satellite_tensor(
            field_id, sat_mean_np, sat_std_np
        )  # Shape [1, 10, 3]

        # Retrieve raw satellite sequence from field service for transparent reporting
        raw_sequence = self.field_service.get_satellite_sequence(canonical_field_id)
        if raw_sequence is None:
            raise SatelliteDataUnavailableError(f"Raw sequence unavailable for field {canonical_field_id}")

        # Retrieve authoritative observation dates if recorded
        field_dates = self.field_service._field_dates.get(canonical_field_id) or []

        # 4. Compute Base Multimodal Model Predictions
        with torch.no_grad():
            full_logits, attention_weights = multimodal_model(img_embedding, sat_tensor)
            probs = torch.softmax(full_logits, dim=-1)[0]
            pred_idx = int(torch.argmax(full_logits, dim=-1).item())
            pred_class = class_names[pred_idx]
            pred_conf = float(probs[pred_idx].item())

        # 5. Determine and Validate Target Explanation Class
        resolved_target_idx = pred_idx
        if target_index is not None:
            if not (0 <= target_index < len(class_names)):
                raise ValueError(
                    f"Invalid target_index '{target_index}'. Must be an integer between 0 and {len(class_names) - 1}."
                )
            resolved_target_idx = target_index
        elif target_class is not None:
            clean_class = str(target_class).strip().lower()
            if clean_class not in class_names:
                raise ValueError(
                    f"Invalid target_class '{target_class}'. Must be one of the 11 multimodal classes: {', '.join(class_names)}"
                )
            resolved_target_idx = class_names.index(clean_class)

        resolved_target_class = class_names[resolved_target_idx]
        target_logit = float(full_logits[0, resolved_target_idx].item())

        # 6. Instantiate Wrapper and Run GradientExplainer
        wrapper = SatelliteClassWrapper(multimodal_model, img_embedding, resolved_target_idx)
        wrapper.eval()

        eval_nsamples = nsamples or config.SHAP_NSAMPLES
        explainer = shap.GradientExplainer(wrapper, self._normalized_background)

        try:
            shap_values = explainer.shap_values(sat_tensor, nsamples=eval_nsamples)
            shap_array = np.squeeze(np.asarray(shap_values))  # Shape: (10, 3)
        except Exception as exc:
            logger.error("GradientExplainer calculation failed: %s", exc)
            raise RuntimeError(f"SHAP explanation calculation failed: {exc}") from exc

        if shap_array.shape != (config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES):
            raise ValueError(
                f"Unexpected SHAP array shape {shap_array.shape}; expected ({config.SATELLITE_TIMESTEPS}, {config.NUM_SATELLITE_FEATURES})"
            )

        if not np.isfinite(shap_array).all():
            raise ValueError("Computed SHAP attributions contain NaN or Infinite numerical values.")

        # 7. Construct Timestep Feature Attributions (30 entries)
        feature_names = config.SATELLITE_FEATURES  # ["NDVI", "NDRE", "GNDVI"]
        norm_values = sat_tensor[0].detach().cpu().numpy()

        timestep_attributions = []
        for t in range(config.SATELLITE_TIMESTEPS):
            obs_date = field_dates[t] if (field_dates and t < len(field_dates)) else None
            for j, feat in enumerate(feature_names):
                val = float(shap_array[t, j])
                contrib = "positive" if val > 1e-6 else ("negative" if val < -1e-6 else "neutral")
                timestep_attributions.append({
                    "timestep": t + 1,
                    "observation_date": obs_date,
                    "feature": feat,
                    "satellite_value_raw": round(float(raw_sequence[t, j]), 4),
                    "satellite_value_normalized": round(float(norm_values[t, j]), 4),
                    "shap_value": round(val, 6),
                    "contribution": contrib,
                    "absolute_shap_value": round(abs(val), 6),
                })

        # 8. Feature-Level Summaries
        feature_summaries = []
        for j, feat in enumerate(feature_names):
            vals = shap_array[:, j]
            pos_sum = float(vals[vals > 0].sum())
            neg_sum = float(vals[vals < 0].sum())
            feature_summaries.append({
                "feature": feat,
                "mean_absolute_shap": round(float(np.abs(vals).mean()), 6),
                "positive_shap_sum": round(pos_sum, 6),
                "negative_shap_sum": round(neg_sum, 6),
                "net_shap": round(float(vals.sum()), 6),
            })

        # 9. Ranked Strongest Positive and Negative Contributions
        sorted_by_abs = sorted(timestep_attributions, key=lambda x: x["absolute_shap_value"], reverse=True)

        pos_items = [x for x in sorted_by_abs if x["shap_value"] > 0]
        neg_items = [x for x in sorted_by_abs if x["shap_value"] < 0]

        top_positive = []
        for rank, item in enumerate(pos_items[:5], start=1):
            top_positive.append({
                "rank": rank,
                "timestep": item["timestep"],
                "observation_date": item.get("observation_date"),
                "feature": item["feature"],
                "satellite_value_raw": item["satellite_value_raw"],
                "shap_value": item["shap_value"],
                "direction": "positive",
                "impact_description": (
                    f"Timestep {item['timestep']} {item['feature']} ({item['satellite_value_raw']}) "
                    f"increased the {resolved_target_class} logit score by +{item['shap_value']:.4f} "
                    f"relative to the background reference."
                ),
            })

        top_negative = []
        for rank, item in enumerate(neg_items[:5], start=1):
            top_negative.append({
                "rank": rank,
                "timestep": item["timestep"],
                "observation_date": item.get("observation_date"),
                "feature": item["feature"],
                "satellite_value_raw": item["satellite_value_raw"],
                "shap_value": item["shap_value"],
                "direction": "negative",
                "impact_description": (
                    f"Timestep {item['timestep']} {item['feature']} ({item['satellite_value_raw']}) "
                    f"decreased the {resolved_target_class} logit score by {item['shap_value']:.4f} "
                    f"relative to the background reference."
                ),
            })

        # 10. Assemble and Return Response Dictionary
        return {
            "status": "success",
            "field_id": canonical_field_id,
            "predicted_class": pred_class,
            "predicted_index": pred_idx,
            "confidence": round(pred_conf, 4),
            "target_class": resolved_target_class,
            "target_index": resolved_target_idx,
            "explanation_target_model": "TemporalCrossAttentionModel (Controlled Step 7L)",
            "explanation_scope": "conditional_satellite_input",
            "explanation_modality": "Satellite Temporal Time-Series (conditioned on EfficientNet-B4 image features)",
            "input_feature_names": feature_names,
            "shap_dimensions": [config.SATELLITE_TIMESTEPS, config.NUM_SATELLITE_FEATURES],
            "explanation_method": "GradientExplainer",
            "background_samples_count": len(self._raw_background),
            "nsamples": eval_nsamples,
            "target_logit": round(target_logit, 4),
            "feature_importance_summary": feature_summaries,
            "top_positive_contributions": top_positive,
            "top_negative_contributions": top_negative,
            "timestep_attributions": timestep_attributions,

            "limitations_note": (
                "SHAP attributions quantify the marginal contribution of temporal Sentinel-2 vegetation indices "
                "relative to a 20-field background baseline for the selected disease logit; they represent model feature "
                "attribution, not direct biological causation or lesion detection."
            ),
        }


# Singleton accessor
shap_service = SHAPService.get_instance()
