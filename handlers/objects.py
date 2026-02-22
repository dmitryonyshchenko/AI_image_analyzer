"""
Handler: Object Detection
Detects large, identifiable objects in the image.
Uses a 10-colour palette — each unique object class gets its own colour.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label, build_color_map

DEFAULT_COLOR = "#FF9100"


class ObjectItem(BaseModel):
    label:       str    # free-form object class name
    bbox:        list[int]
    description: str
    confidence:  float


class AiResponse(BaseModel):
    objects: list[ObjectItem]


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Analyze the image and identify all large, clearly recognizable objects.\n\n"
        f"Only include objects you can identify with at least {pct}% confidence.\n"
        "Skip small, secondary, or background elements.\n\n"
        "For each object provide:\n"
        "- label: short object class name in English (e.g. \"car\", \"tree\", \"bicycle\", \"dog\")\n"
        "- bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "- description: one sentence describing the object\n"
        "- confidence: detection confidence as float 0.0 to 1.0\n\n"
        "Return an empty objects array if nothing qualifies."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    items      = ai_raw.get("objects", [])
    model_name = ai_raw.get("_model", "")

    # Assign palette colours dynamically by first-seen label order
    label_colors = build_color_map(items)

    image     = open_image(original_path)
    annotated = draw_boxes(image, items, label_colors, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    # Result table: unique classes with counts
    class_counts: dict[str, int] = {}
    for item in items:
        lbl = item.get("label", "unknown")
        class_counts[lbl] = class_counts.get(lbl, 0) + 1

    result_table = [
        {"field": lbl.capitalize(), "value": str(cnt)}
        for lbl, cnt in class_counts.items()
    ]
    result_table.append({"field": "Total objects", "value": str(len(items))})

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
