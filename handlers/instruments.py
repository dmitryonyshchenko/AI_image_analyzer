"""
Handler: Instrument Reading
Reads values from gauges, meters, speedometers, and dashboards.
"""
import os
from pydantic import BaseModel

from ai_client import call_ai
from image_processor import open_image, save_image, draw_boxes, draw_model_label, build_color_map

DEFAULT_COLOR = "#FF9100"


class InstrumentItem(BaseModel):
    label:      str    # e.g. "speedometer", "odometer", "gas meter"
    bbox:       list[int]
    reading:    str    # current value shown (e.g. "120")
    unit:       str    # unit if determinable (e.g. "km/h"), else ""
    confidence: float


class ReadingRow(BaseModel):
    parameter: str   # e.g. "Speed", "Distance", "Gas volume"
    value:     str   # e.g. "120 km/h", "130 m³"


class AiResponse(BaseModel):
    objects:  list[InstrumentItem]
    readings: list[ReadingRow]


def _build_prompt(threshold: float) -> str:
    pct = int(threshold * 100)
    return (
        "Analyze this image and identify the main instruments, gauges, meters, or dashboard displays.\n\n"
        f"Only include instruments you can read with at least {pct}% confidence.\n\n"
        "For each instrument provide:\n"
        "- label: instrument type (e.g. \"speedometer\", \"odometer\", \"gas meter\", "
        "\"temperature gauge\", \"fuel gauge\")\n"
        "- bbox: [y_min, x_min, y_max, x_max] integers 0-1000\n"
        "- reading: the current value shown on the instrument as a string\n"
        "- unit: unit of measurement if known (e.g. \"km/h\", \"m³\", \"°C\"), else empty string\n"
        "- confidence: your reading confidence as float 0.0 to 1.0\n\n"
        "Also provide a summary readings list:\n"
        "- parameter: descriptive name (e.g. \"Speed\", \"Distance\", \"Gas volume\", "
        "\"Temperature\"). If the parameter type is unclear but the value is visible, use \"Value\".\n"
        "- value: value with unit (e.g. \"120 km/h\", \"120 000 km\", \"130 m³\")\n\n"
        "Return empty lists if no instruments are visible."
    )


def process(original_path: str, job_dir: str, stem: str, ext: str, config: dict) -> dict:
    threshold = config.get("confidence_threshold", 0.70)
    prompt    = _build_prompt(threshold)

    try:
        ai_raw = call_ai(original_path, prompt, AiResponse)
    except Exception as e:
        return {"annotated_path": None, "error": str(e), "result_table": None, "ai_raw": {}, "prompt": prompt}

    items      = ai_raw.get("objects", [])
    readings   = ai_raw.get("readings", [])
    model_name = ai_raw.get("_model", "")

    # Colour per instrument type
    label_colors = build_color_map(items)

    image     = open_image(original_path)
    annotated = draw_boxes(image, items, label_colors, DEFAULT_COLOR)
    annotated = draw_model_label(annotated, model_name)

    annotated_path = os.path.join(job_dir, f"{stem}_annotated.{ext}")
    save_image(annotated, annotated_path)

    result_table = [
        {"field": r.get("parameter", "—"), "value": r.get("value", "—")}
        for r in readings
    ] if readings else [{"field": "Result", "value": "No instruments detected"}]

    return {
        "annotated_path": annotated_path,
        "error":          None,
        "result_table":   result_table,
        "ai_raw":         ai_raw,
        "prompt":         prompt,
    }
