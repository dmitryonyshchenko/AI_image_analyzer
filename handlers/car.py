"""
Handler: Car Valuation
Identifies the main vehicle in the image, extracts plate, make, model, colour,
country, possible violations, and estimates the car's market value in USD.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label

LABEL_COLORS: dict[str, str] = {
    "vehicle":       "#2979FF",
    "license_plate": "#FF9100",
}
DEFAULT_COLOR = "#999999"


class BBoxItem(BaseModel):
    label:       str
    bbox:        list[int]
    description: str
    confidence:  float


class ViolationInfo(BaseModel):
    type:        str    # e.g. "wrong parking", "blocking fire lane"
    probability: float  # 0.0 – 1.0


class AiResponse(BaseModel):
    objects:         list[BBoxItem]
    make:            str
    model:           str
    color:           str
    plate_text:      str
    country:         str
    confidence:      float
    violations:      list[ViolationInfo]
    value_usd_from:  int    # estimated market value lower bound in USD
    value_usd_to:    int    # estimated market value upper bound in USD
    value_note:      str    # brief explanation of the estimate


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Analyze this image and find the MAIN vehicle (car, truck, or motorcycle).\n\n"
        "Return a JSON object with:\n\n"
        "objects — list of items to annotate:\n"
        "  - label: exactly \"vehicle\" or \"license_plate\"\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - description: plate text or brief vehicle description\n"
        "  - confidence: float 0.0 to 1.0\n\n"
        "make        — vehicle manufacturer brand (empty string if unknown)\n"
        "model       — vehicle model name (empty string if unknown)\n"
        "color       — main body color (empty string if unknown)\n"
        "plate_text  — license plate number (empty string if not readable)\n"
        "country     — country/region inferred from plate format (empty string if unknown)\n"
        "confidence  — overall detection confidence float 0.0 to 1.0\n\n"
        "violations — list of possible traffic violations visible in the image:\n"
        "  - type: short description (e.g. \"wrong parking\", \"blocking fire lane\",\n"
        "          \"no parking zone\", \"double parking\")\n"
        f"  - probability: float 0.0 to 1.0 (only include if probability ≥ {pct/100:.2f})\n\n"
        "value_usd_from — estimated lower bound of current market value in USD (integer, 0 if unknown)\n"
        "value_usd_to   — estimated upper bound of current market value in USD (integer, 0 if unknown)\n"
        "value_note     — one sentence explaining the estimate "
        "(model year, trim level, mileage assumption, market region, etc.)\n\n"
        "Return empty lists and empty strings if nothing is found."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    objects    = ai_raw.get("objects", [])
    violations = ai_raw.get("violations", [])
    model_name = ai_raw.get("_model", "")

    image     = open_image(original_path)
    annotated = draw_boxes(image, objects, LABEL_COLORS, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    conf_pct    = int(ai_raw.get("confidence", 0.0) * 100)
    val_from    = ai_raw.get("value_usd_from", 0)
    val_to      = ai_raw.get("value_usd_to",   0)
    val_note    = ai_raw.get("value_note",      "") or ""

    if val_from and val_to:
        value_str = f"${val_from:,} – ${val_to:,}"
    elif val_from or val_to:
        value_str = f"~${max(val_from, val_to):,}"
    else:
        value_str = "—"

    result_table = [
        {"field": "Make",            "value": ai_raw.get("make",  "")     or "—"},
        {"field": "Model",           "value": ai_raw.get("model", "")     or "—"},
        {"field": "Color",           "value": ai_raw.get("color", "")     or "—"},
        {"field": "Plate",           "value": ai_raw.get("plate_text", "") or "—"},
        {"field": "Country",         "value": ai_raw.get("country", "")   or "—"},
        {"field": "Confidence",      "value": f"{conf_pct}%"},
        {"field": "💰 Est. Value",   "value": value_str},
    ]
    if val_note:
        result_table.append({"field": "Value note", "value": val_note})

    for v in violations:
        prob = int(v.get("probability", 0) * 100)
        result_table.append({
            "field": "⚠ Possible violation",
            "value": f"{v.get('type', '—')} ({prob}%)",
        })

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
