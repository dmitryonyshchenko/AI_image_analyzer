"""
Handler: Satellite Image Analysis
Analyzes satellite or aerial imagery: landscape type, area classification
(civilian/military/industrial/etc.), and notable objects with bounding boxes.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label, build_color_map, COLOR_PALETTE

DEFAULT_COLOR = "#FF9100"


class DetectedObject(BaseModel):
    label:       str    # e.g. "aircraft", "runway", "building cluster", "ship", "tank"
    bbox:        list[int]
    description: str
    confidence:  float
    count:       int    # number of similar objects inside this bbox (1 if single)


class AreaAnalysis(BaseModel):
    landscape_type:  str         # e.g. "urban", "coastal", "arid desert", "forested", "agricultural"
    area_type:       str         # e.g. "international airport", "military airbase", "industrial zone"
    classification:  str         # "civilian", "military", "industrial", "residential",
                                 # "nature", "agricultural", "mixed"
    country_region:  str         # likely country or region if identifiable (empty if unknown)
    description:     str         # 2-3 sentence overview of what the image shows
    notable_objects: list[str]   # key specific observations, e.g. "~12 fighter jets on apron"


class AiResponse(BaseModel):
    objects:  list[DetectedObject]
    analysis: AreaAnalysis


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "This is a satellite or aerial photograph. Analyze it thoroughly.\n\n"
        f"Only include detections with confidence ≥ {pct}%.\n"
        "Return at most 15 objects — prioritize the most significant ones.\n\n"
        "Return a JSON object with:\n\n"
        "objects — bounding boxes around notable objects or zones (max 15):\n"
        "  - label: concise object name "
        "(e.g. \"aircraft\", \"runway\", \"ship\", \"fuel tank\", "
        "\"radar dish\", \"building cluster\", \"vehicle\", \"crater\", "
        "\"bridge\", \"agricultural field\", \"forest patch\")\n"
        "  - bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "  - description: very short phrase, max 8 words\n"
        "  - confidence: float 0.0 to 1.0\n"
        "  - count: number of individual items of this type inside this bbox "
        "(use 1 for a single object, use higher numbers for groups like "
        "\"8 aircraft\", \"~20 vehicles\")\n\n"
        "analysis — overall image assessment:\n"
        "  - landscape_type: dominant terrain type "
        "(e.g. \"urban\", \"coastal\", \"arid\", \"forested\", "
        "\"mountainous\", \"agricultural\", \"arctic\")\n"
        "  - area_type: primary function or facility type "
        "(e.g. \"international airport\", \"military airbase\", "
        "\"commercial seaport\", \"oil refinery\", \"residential district\", "
        "\"nuclear facility\", \"railway depot\", \"open countryside\")\n"
        "  - classification: dominant use category — one of: "
        "\"civilian\", \"military\", \"industrial\", \"residential\", "
        "\"nature\", \"agricultural\", \"mixed\"\n"
        "  - country_region: likely country or geographic region "
        "based on visible clues (empty string if cannot be determined)\n"
        "  - description: 2-3 sentence factual overview of what the image shows\n"
        "  - notable_objects: list of key specific findings "
        "(e.g. \"Approximately 14 combat aircraft visible on apron\", "
        "\"Large fuel storage farm, ~6 tanks\", "
        "\"Hardened aircraft shelters typical of military base\")\n\n"
        "Return empty objects list and empty strings if the image is not a satellite/aerial view."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    objects    = ai_raw.get("objects", [])
    analysis   = ai_raw.get("analysis", {})
    model_name = ai_raw.get("_model", "")

    # Enrich label with count for drawing (e.g. "aircraft ×8")
    draw_items = []
    for obj in objects:
        cnt = obj.get("count", 1)
        label = obj.get("label", "")
        draw_items.append({
            **obj,
            "label": f"{label} ×{cnt}" if cnt > 1 else label,
        })

    color_map = build_color_map(draw_items, COLOR_PALETTE)

    image     = open_image(original_path)
    annotated = draw_boxes(image, draw_items, color_map, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    a = analysis if isinstance(analysis, dict) else {}

    result_table = [
        {"field": "🌍 Landscape",      "value": a.get("landscape_type", "") or "—"},
        {"field": "🏭 Area type",       "value": a.get("area_type",      "") or "—"},
        {"field": "🔖 Classification",  "value": a.get("classification", "") or "—"},
        {"field": "📍 Region",          "value": a.get("country_region", "") or "—"},
        {"field": "📝 Overview",        "value": a.get("description",    "") or "—"},
    ]

    notable = a.get("notable_objects", [])
    if notable:
        result_table.append({"field": "─── Key findings ───", "value": ""})
        for item in notable:
            result_table.append({"field": "🔍", "value": item})

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
