"""
Paddy Farming Assistant - PDF Report Generation Service (STEP 11I.4)
Compiles elegant, printable diagnostic dossiers using ReportLab,
enforcing safe artifact storage, strict path traversal guards,
and complete privacy masking (zero raw coordinates or server paths).
"""

import io
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from app import config

logger = logging.getLogger(__name__)

# Primary Agricultural Color Palette
PRIMARY_GREEN = colors.HexColor("#1B5E20")    # Deep forest green
SECONDARY_GREEN = colors.HexColor("#2E7D32")  # Foliage green
LIGHT_GREEN_BG = colors.HexColor("#E8F5E9")   # Soft green tint
TEXT_DARK = colors.HexColor("#212121")        # Off-black for crisp reading
TEXT_MUTED = colors.HexColor("#546E7A")       # Slate grey
BORDER_GREY = colors.HexColor("#CFD8DC")      # Light border
ALERT_AMBER_BG = colors.HexColor("#FFF8E1")   # Disclaimer amber tint
ALERT_AMBER_BORDER = colors.HexColor("#FFB300")


def resolve_report_path(relative_path: str) -> Path:
    """
    Safely resolves a relative artifact storage path within REPORTS_STORAGE_DIR.
    Guards strictly against path traversal attempts.
    """
    clean_rel = Path(relative_path)
    if clean_rel.is_absolute() or ".." in clean_rel.parts:
        logger.warning("Security violation: Path traversal detected in '%s'", relative_path)
        raise ValueError("Invalid artifact path: Path traversal is prohibited.")

    storage_root = config.REPORTS_STORAGE_DIR.resolve()
    resolved = (storage_root / clean_rel).resolve()

    if not str(resolved).startswith(str(storage_root)):
        logger.warning("Security violation: Target path '%s' escapes storage root '%s'", resolved, storage_root)
        raise ValueError("Access denied: Artifact path escapes storage directory.")

    return resolved


class PDFReportService:
    """
    Service responsible for compiling ReportLab PDF dossiers from report metadata
    and safely reading/writing artifacts to persistent storage.
    """

    @staticmethod
    def generate_pdf_bytes(
        report_id: uuid.UUID,
        metadata: Dict[str, Any],
        title: str,
        summary: Optional[str] = None,
    ) -> bytes:
        """
        Compiles a high-quality agricultural diagnostic PDF dossier from report metadata.
        Returns the raw PDF binary bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()

        # Custom Typography Styles
        style_header_title = ParagraphStyle(
            "DocHeaderTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=PRIMARY_GREEN,
        )

        style_header_sub = ParagraphStyle(
            "DocHeaderSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=TEXT_MUTED,
        )

        style_section_heading = ParagraphStyle(
            "DocSectionHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=SECONDARY_GREEN,
            spaceBefore=10,
            spaceAfter=6,
        )

        style_body = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=TEXT_DARK,
        )

        style_body_bold = ParagraphStyle(
            "DocBodyBold",
            parent=style_body,
            fontName="Helvetica-Bold",
        )

        style_disclaimer = ParagraphStyle(
            "DocDisclaimer",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#4E342E"),
        )

        story: List[Any] = []

        # 1. Header Banner
        story.append(Paragraph("PADDY FARMING ASSISTANT", style_header_title))
        story.append(Paragraph("Agricultural AI Disease Detection Diagnostic Dossier & Decision Support", style_header_sub))
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width="100%", thickness=2, color=SECONDARY_GREEN, spaceAfter=10))

        # 2. Executive Metadata Box
        pred_id = metadata.get("prediction_id", "N/A")
        now_iso = metadata.get("report_generated_at", datetime.now(timezone.utc).isoformat())
        pred_ts = metadata.get("prediction_timestamp")
        pred_ts_str = (pred_ts[:19].replace("T", " ") + " UTC") if pred_ts else "N/A"
        mode_val = metadata.get("prediction_mode", "image_only")
        mode_str = mode_val.replace("_", " ").title() if mode_val else "N/A"

        field_ext = metadata.get("field_external_id")
        field_nm = metadata.get("field_name")
        field_uuid = metadata.get("field_id")
        if field_ext and field_nm:
            field_str = f"{field_ext} — {field_nm}"
        elif field_ext:
            field_str = field_ext
        elif field_nm:
            field_str = field_nm
        elif field_uuid:
            field_str = f"Field UUID: {str(field_uuid)[:13]}..."
        else:
            field_str = "Standalone Leaf Specimen"

        meta_table_data = [
            [
                Paragraph("<b>Report Identifier:</b>", style_body),
                Paragraph(str(report_id), style_body),
                Paragraph("<b>Report Generated:</b>", style_body),
                Paragraph(now_iso[:19].replace("T", " ") + " UTC", style_body),
            ],
            [
                Paragraph("<b>Prediction Identifier:</b>", style_body),
                Paragraph(str(pred_id), style_body),
                Paragraph("<b>Prediction Timestamp:</b>", style_body),
                Paragraph(pred_ts_str, style_body),
            ],
            [
                Paragraph("<b>Prediction Mode:</b>", style_body),
                Paragraph(mode_str, style_body),
                Paragraph("<b>Agricultural Parcel:</b>", style_body),
                Paragraph(field_str, style_body),
            ],
        ]

        meta_table = Table(meta_table_data, colWidths=[120, 140, 130, 130])
        meta_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREEN_BG),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(meta_table)
        story.append(Spacer(1, 12))

        # 3. Primary Diagnostic Findings
        story.append(Paragraph("1. Primary Diagnostic Classification", style_section_heading))

        disease_raw = metadata.get("predicted_disease", "unknown")
        disease_clean = disease_raw.replace("_", " ").title()
        conf_val = float(metadata.get("confidence", 0.0))
        conf_pct = f"{conf_val:.1%}"
        mode = metadata.get("prediction_mode", "image_only")
        model_nm = metadata.get("model_name", "EfficientNet-B4")
        is_healthy = metadata.get("is_healthy", False)
        low_conf = metadata.get("low_confidence", False)

        if is_healthy:
            status_text = "NORMAL (HEALTHY)"
            status_color = SECONDARY_GREEN
        elif low_conf:
            status_text = "LOW CONFIDENCE (< 60%) — RE-INSPECTION ADVISED"
            status_color = colors.HexColor("#E65100")
        else:
            status_text = "PATHOGEN DETECTED"
            status_color = colors.HexColor("#C62828")

        diag_data = [
            [
                Paragraph("<b>Predicted Diagnosis:</b>", style_body),
                Paragraph(f"<font size=11 color='{PRIMARY_GREEN.hexval()}'><b>{disease_clean}</b></font>", style_body),
                Paragraph("<b>Diagnostic Status:</b>", style_body),
                Paragraph(f"<font color='{status_color.hexval()}'><b>{status_text}</b></font>", style_body),
            ],
            [
                Paragraph("<b>Confidence Probability:</b>", style_body),
                Paragraph(f"<b>{conf_pct}</b> (Softmax Probability)", style_body),
                Paragraph("<b>AI Model Architecture:</b>", style_body),
                Paragraph(f"{model_nm} ({mode})", style_body),
            ],
            [
                Paragraph("<b>Specimen Fingerprint:</b>", style_body),
                Paragraph(str(metadata.get("image_sha256", "N/A"))[:24] + "...", style_body),
                Paragraph("<b>Class Label Index:</b>", style_body),
                Paragraph(str(metadata.get("predicted_class_index", "N/A")), style_body),
            ],
        ]

        diag_table = Table(diag_data, colWidths=[120, 140, 130, 130])
        diag_table.setStyle(
            TableStyle([
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(diag_table)
        story.append(Spacer(1, 10))

        # 4. Top-K Candidate Predictions
        top_k = metadata.get("top_k_predictions", [])
        cand_list = []
        if top_k and isinstance(top_k, list):
            for cand in top_k:
                if isinstance(cand, dict):
                    c_name = (cand.get("disease") or cand.get("class") or cand.get("disease_name") or "N/A").replace("_", " ").title()
                    c_idx = str(cand.get("index") if cand.get("index") is not None else cand.get("class_index", "N/A"))
                    c_prob = float(cand.get("probability") if cand.get("probability") is not None else cand.get("confidence", 0.0))
                    cand_list.append((c_name, c_idx, c_prob))
            cand_list.sort(key=lambda x: x[2], reverse=True)

        if not cand_list:
            pred_idx = str(metadata.get("predicted_class_index", "N/A"))
            cand_list = [(disease_clean, pred_idx, conf_val)]

        story.append(Paragraph("2. Ranked Candidate Probabilities", style_section_heading))
        cand_rows = [
            [
                Paragraph("<b>Rank</b>", style_body_bold),
                Paragraph("<b>Condition / Disease Label</b>", style_body_bold),
                Paragraph("<b>Class Index</b>", style_body_bold),
                Paragraph("<b>Probability</b>", style_body_bold),
            ]
        ]
        for idx, (c_name, c_idx, c_prob) in enumerate(cand_list[:3], start=1):
            cand_rows.append([
                Paragraph(f"#{idx}", style_body),
                Paragraph(c_name, style_body),
                Paragraph(c_idx, style_body),
                Paragraph(f"{c_prob:.2%}", style_body),
            ])

        cand_table = Table(cand_rows, colWidths=[50, 240, 100, 130])
        cand_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F8E9")),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ])
        )
        story.append(cand_table)
        story.append(Spacer(1, 10))

        # 5. Multimodal Sequence Attention (if present)
        attn_weights = metadata.get("attention_weights")
        if mode == "multimodal" and attn_weights and isinstance(attn_weights, list):
            story.append(Paragraph("3. Multimodal Temporal Satellite Cross-Attention", style_section_heading))
            story.append(
                Paragraph(
                    "Relative influence weight (%) of each 10-day Sentinel-2 satellite vegetation observation "
                    "in fusing satellite canopy dynamics with the leaf visual embedding:",
                    style_body,
                )
            )
            story.append(Spacer(1, 4))

            attn_headers = [Paragraph(f"<b>T{i+1}</b>", style_body_bold) for i in range(len(attn_weights))]
            attn_vals = [Paragraph(f"{float(w):.1%}", style_body) for w in attn_weights]
            attn_table = Table([attn_headers, attn_vals], colWidths=[52] * len(attn_weights))
            attn_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREEN_BG),
                    ("BOX", (0, 0), (-1, -1), 1, BORDER_GREY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ])
            )
            story.append(attn_table)
            story.append(Spacer(1, 10))

        # 6. Agronomic Advisory Recommendations
        story.append(Paragraph("4. Agronomic Advisory & Guidance", style_section_heading))
        if is_healthy:
            advisory_body = summary or (
                f"AI Diagnostic Report for Healthy Leaf Specimen with {conf_pct} confidence using {model_nm} in {mode} mode. "
                "Definitive signs of healthy foliage confirmed. No pathogenic lesion activity detected. "
                "Maintain standard crop nutrition, water management, and regular pest surveillance."
            )
        else:
            advisory_body = summary or (
                f"AI Diagnostic Report for {disease_clean} with {conf_pct} confidence using {model_nm} in {mode} mode. "
                f"Definitive signs consistent with {disease_clean} identified. Consult local agricultural extension officers "
                "before applying any chemical fungicides or pesticides."
            )
        story.append(Paragraph(advisory_body, style_body))
        story.append(Spacer(1, 8))

        if is_healthy:
            recs = [
                "• Specimen displays normal healthy leaf coloration and intact cellular tissue.",
                "• Maintain balanced N-P-K fertilizer schedules; avoid excessive urea top-dressing.",
                "• Continue routine weekly scouting for early foliar lesion emergence.",
            ]
        elif disease_raw == "tungro":
            recs = [
                "• Viral infection transmitted by Green Leafhopper (Nephotettix virescens).",
                "• Immediately scout for leafhopper vectors and consider targeted vector suppression.",
                "• Rogue and bury heavily infected, stunted hills to prevent field-wide vector spread.",
                "• Apply balanced fertilizer and avoid standing stagnant water across infested plots.",
            ]
        elif disease_raw in ("blast", "brown_spot", "sheath_blight"):
            recs = [
                "• Fungal foliar pathogen identified; inspect collar rot and panicle blast symptoms.",
                "• Consult agricultural extension authorities for recommended fungicide active ingredients.",
                "• Regulate field water level and ensure proper spacing for aeration between crop rows.",
                "• Suspend immediate nitrogenous fertilizer application until fungal progression halts.",
            ]
        elif "blight" in disease_raw or "bacterial" in disease_raw:
            recs = [
                "• Bacterial pathogen indicated; avoid field operations when leaves are wet with morning dew.",
                "• Ensure field drainage is unobstructed; bacterial ooze spreads rapidly in standing floodwater.",
                "• Use certified disease-free seed cultivars for following planting rotations.",
            ]
        else:
            recs = [
                "• Observe field progression and sample multiple symptomatic plants across the parcel.",
                "• Take specimen photographs under diffused daylight for secondary extension evaluation.",
                "• Consult the district agriculture officer prior to applying any chemical remedies.",
            ]

        for r in recs:
            story.append(Paragraph(r, style_body))
        story.append(Spacer(1, 12))

        # 7. AI Decision Support Disclaimer (Tinted Box)
        disclaimer_text = metadata.get("disclaimer") or (
            "DISCLAIMER: This diagnostic advisory is generated by artificial intelligence "
            "(EfficientNet-B4 / TemporalCrossAttention) and serves solely as informational decision support. "
            "It does not constitute a guaranteed clinical diagnosis or professional agricultural certification. "
            "Field verification by a certified agronomist is recommended prior to applying chemical treatments."
        )

        disclaimer_box = Table(
            [[Paragraph(f"<b>LEGAL & SCIENTIFIC DECISION SUPPORT NOTICE:</b><br/>{disclaimer_text}", style_disclaimer)]],
            colWidths=[520],
        )
        disclaimer_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), ALERT_AMBER_BG),
                ("BOX", (0, 0), (-1, -1), 1, ALERT_AMBER_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        story.append(KeepTogether(disclaimer_box))

        # Build document
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    @classmethod
    def save_pdf_artifact(
        cls,
        report_id: uuid.UUID,
        prediction_id: Optional[uuid.UUID],
        pdf_bytes: bytes,
    ) -> str:
        """
        Saves PDF bytes to persistent disk storage under REPORTS_STORAGE_DIR/diagnostic.
        Returns the safe relative artifact path key (e.g. 'diagnostic/report_{pred_id}_{rep_id}.pdf').
        """
        pred_key = str(prediction_id) if prediction_id else "standalone"
        filename = f"report_{pred_key}_{report_id.hex[:8]}.pdf"
        rel_dir = Path("diagnostic")
        full_dir = config.REPORTS_STORAGE_DIR / rel_dir
        full_dir.mkdir(parents=True, exist_ok=True)

        target_path = full_dir / filename
        with open(target_path, "wb") as f:
            f.write(pdf_bytes)

        rel_key = str(rel_dir / filename).replace("\\", "/")
        logger.info("Saved PDF artifact (%d bytes) to safe storage key '%s'.", len(pdf_bytes), rel_key)
        return rel_key

    @classmethod
    def read_pdf_artifact(cls, relative_path: str) -> bytes:
        """
        Safely reads PDF artifact bytes from disk storage, verifying path bounds.
        Raises FileNotFoundError if file is missing, or ValueError if empty or invalid.
        """
        resolved = resolve_report_path(relative_path)
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Report artifact '{relative_path}' not found on storage disk.")

        with open(resolved, "rb") as f:
            content = f.read()

        if len(content) == 0:
            raise ValueError(f"Report artifact '{relative_path}' is empty (0 bytes).")

        if not content.startswith(b"%PDF-"):
            raise ValueError(f"Report artifact '{relative_path}' is corrupted: missing PDF magic header.")

        return content
